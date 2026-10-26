"""Local ComfyUI adapter for genuine diffusion outputs, separate from Neural Core.
No model download, arbitrary workflows, remote URLs, shell or cloud credentials.
"""
from __future__ import annotations
import copy
import hashlib
import json
import mimetypes
from pathlib import Path
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from memory.vault import data_directory

IMAGE_NODES=['CheckpointLoaderSimple','CLIPTextEncode','EmptyLatentImage','KSampler','VAEDecode','SaveImage']
VIDEO_NODES=['UNETLoader','CLIPLoader','VAELoader','CLIPTextEncode','EmptyHunyuanLatentVideo','ModelSamplingSD3','KSampler','VAEDecode','SaveWEBM']
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def validate_request(value):
    if not isinstance(value,dict):raise ValueError('Solicitação inválida.')
    kind=value.get('kind');prompt=value.get('prompt','');negative=value.get('negative','')
    if kind not in ('image','video') or not isinstance(prompt,str) or not prompt.strip() or len(prompt)>4000 or not isinstance(negative,str) or len(negative)>2000:raise ValueError('Preencha uma descrição de até 4.000 caracteres.')
    result={'kind':kind,'prompt':prompt.strip(),'negative':negative,'style':value.get('style','photo')}
    if result['style'] not in ('photo','cinema','none'):raise ValueError('Estilo inválido.')
    for key,default,low,high in [('steps',20,1,50),('seed',0,0,2147483647),('width',512,256,1536),('height',512,256,1536)]:
        v=value.get(key,default)
        if type(v) is not int or not low<=v<=high:raise ValueError('Parâmetro '+key+' fora do limite.')
        result[key]=v
    if result['width']%16 or result['height']%16 or result['width']*result['height']>1572864:raise ValueError('Use dimensões múltiplas de 16, até 1,5 megapixel.')
    cfg=value.get('cfg',6)
    if type(cfg) not in (int,float) or not 1<=cfg<=12:raise ValueError('CFG deve estar entre 1 e 12.')
    result['cfg']=cfg
    for key in (['checkpoint'] if kind=='image' else ['diffusion_model','text_encoder','vae']):
        v=value.get(key)
        if not isinstance(v,str) or not v or len(v)>256:raise ValueError('Escolha os modelos instalados no motor.')
        result[key]=v
    if kind=='video':
        frames=value.get('frames',49);fps=value.get('fps',16)
        if type(frames) is not int or frames not in (17,33,49,65,81) or type(fps) is not int or fps not in (16,24):raise ValueError('Vídeo deve usar 17 a 81 quadros e 16 ou 24 fps.')
        result.update(frames=frames,fps=fps)
    return result


def workflow(p,prefix):
    prompt=p['prompt']
    if p['style']=='photo':prompt+=', photorealistic, natural lighting, physically plausible materials, fine texture, realistic perspective, balanced exposure'
    if p['style']=='cinema':prompt+=', cinematic realism, coherent scene, natural texture, motivated lighting, detailed environment, realistic optics'
    if p['kind']=='image':
        graph={
          '1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':p['checkpoint']}},
          '2':{'class_type':'CLIPTextEncode','inputs':{'text':prompt,'clip':['1',1]}},
          '3':{'class_type':'CLIPTextEncode','inputs':{'text':p['negative'],'clip':['1',1]}},
          '4':{'class_type':'EmptyLatentImage','inputs':{'width':p['width'],'height':p['height'],'batch_size':1}},
          '5':{'class_type':'KSampler','inputs':{'model':['1',0],'positive':['2',0],'negative':['3',0],'latent_image':['4',0],'seed':p['seed'],'steps':p['steps'],'cfg':p['cfg'],'sampler_name':'euler','scheduler':'normal','denoise':1}},
          '6':{'class_type':'VAEDecode','inputs':{'samples':['5',0],'vae':['1',2]}},
          '7':{'class_type':'SaveImage','inputs':{'images':['6',0],'filename_prefix':prefix}}}
    else:
        graph={
          '1':{'class_type':'UNETLoader','inputs':{'unet_name':p['diffusion_model'],'weight_dtype':'default'}},
          '2':{'class_type':'CLIPLoader','inputs':{'clip_name':p['text_encoder'],'type':'wan','device':'default'}},
          '3':{'class_type':'VAELoader','inputs':{'vae_name':p['vae']}},
          '4':{'class_type':'CLIPTextEncode','inputs':{'text':prompt,'clip':['2',0]}},
          '5':{'class_type':'CLIPTextEncode','inputs':{'text':p['negative'],'clip':['2',0]}},
          '6':{'class_type':'EmptyHunyuanLatentVideo','inputs':{'width':p['width'],'height':p['height'],'length':p['frames'],'batch_size':1}},
          '7':{'class_type':'ModelSamplingSD3','inputs':{'model':['1',0],'shift':8}},
          '8':{'class_type':'KSampler','inputs':{'model':['7',0],'positive':['4',0],'negative':['5',0],'latent_image':['6',0],'seed':p['seed'],'steps':p['steps'],'cfg':p['cfg'],'sampler_name':'uni_pc','scheduler':'simple','denoise':1}},
          '9':{'class_type':'VAEDecode','inputs':{'samples':['8',0],'vae':['3',0]}},
          '10':{'class_type':'SaveWEBM','inputs':{'images':['9',0],'filename_prefix':prefix,'codec':'vp9','fps':p['fps'],'crf':24}}}
    return graph,prompt


class MediaService:
    def __init__(self,root=None):
        self.root=Path(root) if root else data_directory()/'media-ai';self.root.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.port=8188;self.jobs={};self.running=None;self.info={};self.cache=None
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        try:
            saved=json.loads((self.root/'state.json').read_text());self.port=self.validate_port(saved['port'])
            for j in saved.get('jobs',[])[:20]:
                if isinstance(j,dict) and re_uuid(j.get('id')):
                    if j.get('status') in ('queued','running'):j['status']='interrupted';j['message']='Aplicativo foi fechado. Consulte o histórico antes de gerar novamente.'
                    self.jobs[j['id']]=j
        except (OSError,ValueError,KeyError,TypeError):pass
    @staticmethod
    def validate_port(port):
        if type(port) is not int or not 1024<=port<=65535:raise ValueError('Porta local inválida.')
        return port
    def save(self):
        with self.lock:
            target=self.root/'state.json';temporary=self.root/'state.tmp'
            temporary.write_text(json.dumps({'port':self.port,'jobs':list(self.jobs.values())[-20:]},ensure_ascii=False),encoding='utf-8');temporary.replace(target)
    def request(self,path,payload=None,timeout=15):
        url=f'http://127.0.0.1:{self.port}'+path
        req=urllib.request.Request(url,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        try:
            with self.opener.open(req,timeout=timeout) as response:
                data=response.read(2*1024*1024+1)
                if len(data)>2*1024*1024:raise ValueError('Resposta do motor excede o limite.')
                return json.loads(data)
        except urllib.error.HTTPError as exc:
            raise ValueError('Motor recusou a operação (HTTP '+str(exc.code)+'). Verifique os nós e os modelos instalados.') from None
        except (urllib.error.URLError,TimeoutError,OSError):raise ValueError('Motor de IA não respondeu em 127.0.0.1:'+str(self.port)+'. Inicie o ComfyUI neste computador.') from None
    @staticmethod
    def choices(info,node,key):
        inputs=info.get(node,{}).get('input',{});v=inputs.get('required',{}).get(key,inputs.get('optional',{}).get(key))
        return [s for s in v[0][:1000] if isinstance(s,str) and len(s)<=256] if isinstance(v,list) and v and isinstance(v[0],list) else []
    def probe(self,port=None):
        with self.lock:
            if port is not None:
                if self.running:raise ValueError('Aguarde ou cancele o trabalho antes de mudar o motor.')
                self.port=self.validate_port(port);self.cache=None;self.save()
        stats=self.request('/system_stats',timeout=3);info={}
        for node in sorted(set(IMAGE_NODES+VIDEO_NODES)):
            try:info.update(self.request('/object_info/'+node,timeout=3))
            except ValueError:pass
        with self.lock:
            self.info=info;self.cache={'connected':True,'port':self.port,'devices':[{'name':str(d.get('name','Dispositivo'))[:160],'type':str(d.get('type',''))[:40],'vram_total':d.get('vram_total') if type(d.get('vram_total')) in (int,float) else 0} for d in stats.get('devices',[])[:8] if isinstance(d,dict)],'checkpoints':self.choices(info,'CheckpointLoaderSimple','ckpt_name'),
              'diffusion_models':self.choices(info,'UNETLoader','unet_name'),'text_encoders':self.choices(info,'CLIPLoader','clip_name'),'vaes':self.choices(info,'VAELoader','vae_name'),
              'missing_image_nodes':[n for n in IMAGE_NODES if n not in info],'missing_video_nodes':[n for n in VIDEO_NODES if n not in info]}
            return copy.deepcopy(self.cache)
    def list(self):
        with self.lock:return {'port':self.port,'jobs':copy.deepcopy(list(self.jobs.values())[-20:])}
    def submit(self,payload):
        p=validate_request(payload)
        if not self.cache:self.probe()
        pairs=[('checkpoint','CheckpointLoaderSimple','ckpt_name')] if p['kind']=='image' else [('diffusion_model','UNETLoader','unet_name'),('text_encoder','CLIPLoader','clip_name'),('vae','VAELoader','vae_name')]
        if any(p[k] not in self.choices(self.info,n,key) for k,n,key in pairs):raise ValueError('Modelo não encontrado no motor. Atualize o diagnóstico e escolha os modelos instalados.')
        missing=self.cache['missing_'+p['kind']+'_nodes']
        if missing:raise ValueError('Nós ausentes no motor: '+', '.join(missing))
        digest=hashlib.sha256(json.dumps({'port':self.port,'params':p},sort_keys=True).encode()).hexdigest()
        with self.lock:
            for old in reversed(list(self.jobs.values())):
                if old.get('digest')==digest and old.get('status') in ('queued','running','completed'):
                    return {'job':copy.deepcopy(old),'reused':True}
            if self.running:raise ValueError('Há uma geração em andamento. Isso evita carregar dois modelos ao mesmo tempo.')
            identifier=str(uuid.uuid4());graph,effective=workflow(p,'Elysia/'+identifier)
            job={'id':identifier,'status':'queued','kind':p['kind'],'params':p,'effective_prompt':effective,'digest':digest,'created':time.time(),'engine_port':self.port,'outputs':[],'message':'Enviando ao motor…','model_weights_sha256':None}
            self.jobs[identifier]=job;self.running=identifier;self.jobs=dict(list(self.jobs.items())[-20:]);self.save()
            threading.Thread(target=self.run,args=(identifier,graph),daemon=True).start()
            return {'job':copy.deepcopy(job),'reused':False}
    def run(self,identifier,graph):
        try:
            result=({'prompt_id':self.jobs[identifier]['prompt_id']} if graph is None else self.request('/prompt',{'prompt':graph,'client_id':'elysia-'+identifier}))
            if not isinstance(result.get('prompt_id'),str):raise ValueError('Motor não forneceu identificador válido de geração.')
            with self.lock:
                job=self.jobs[identifier]
                job['prompt_id']=result['prompt_id']
                if job['status']=='cancelled':
                    self.cancel_engine(result['prompt_id']);self.save();return
                job.update(status='running',message='Processando no motor de IA. A velocidade depende da GPU e do modelo.');self.save()
            started=time.monotonic()
            while time.monotonic()-started<3600:
                with self.lock:
                    if self.jobs[identifier]['status']=='cancelled':return
                history=self.request('/history/'+urllib.parse.quote(result['prompt_id'],safe=''))
                entry=history.get(result['prompt_id'])
                if entry:
                    if entry.get('status',{}).get('status_str')=='error':raise ValueError('Motor falhou durante a geração. Consulte sua memória disponível e o console do ComfyUI.')
                    outputs=entry.get('outputs',{});descriptors=[]
                    for node in ('7',) if job['kind']=='image' else ('10',):
                        output=outputs.get(node,{})
                        for key in ('images','gifs','videos'):
                            for descriptor in output.get(key,[]):
                                if isinstance(descriptor,dict):descriptors.append(descriptor)
                    if descriptors:
                        files=[self.download(identifier,i,d) for i,d in enumerate(descriptors[:1])]
                        with self.lock:
                            if job['status']=='cancelled':return
                            job.update(status='completed',outputs=files,finished=time.time(),message='Arquivo recebido do motor. Confira o resultado e exporte seus metadados.');self.save()
                        return
                    if entry.get('status',{}).get('completed'):raise ValueError('Motor concluiu sem um arquivo de saída compatível.')
                time.sleep(1)
            raise ValueError('Tempo limite de uma hora. Consulte o histórico do motor antes de repetir.')
        except Exception as exc:
            with self.lock:
                job=self.jobs[identifier]
                if job['status']!='cancelled':job.update(status='failed',message=str(exc)[:600],finished=time.time());self.save()
        finally:
            with self.lock:
                if self.running==identifier:self.running=None
    def download(self,identifier,index,descriptor):
        filename=descriptor.get('filename','');folder=descriptor.get('subfolder','')
        if not isinstance(filename,str) or len(filename)>256 or '/' in filename or '\\' in filename or not isinstance(folder,str) or len(folder)>512 or folder.startswith(('/','\\')) or '..' in folder.replace('\\','/').split('/') or ':' in folder:raise ValueError('Caminho de saída inválido no motor.')
        suffix=Path(filename).suffix.lower()
        if suffix not in ('.png','.jpg','.jpeg','.webp','.webm','.mp4'):raise ValueError('Formato de saída não suportado.')
        target=self.root/(identifier+'-'+str(index)+suffix);temporary=target.with_suffix(suffix+'.part');limit=256*1024*1024 if suffix in ('.webm','.mp4') else 64*1024*1024
        url=f'http://127.0.0.1:{self.port}/view?'+urllib.parse.urlencode({'filename':filename,'subfolder':folder,'type':'output'})
        size=0;sha=hashlib.sha256()
        try:
            with self.opener.open(url,timeout=30) as response,temporary.open('wb') as out:
                while block:=response.read(1024*1024):
                    size+=len(block)
                    if size>limit:raise ValueError('Arquivo gerado excede o limite de download.')
                    sha.update(block);out.write(block)
            if not size:raise ValueError('Motor retornou um arquivo vazio.')
            with temporary.open('rb') as f:head=f.read(16)
            valid=(suffix=='.png' and head.startswith(b'\x89PNG\r\n\x1a\n') or suffix in ('.jpg','.jpeg') and head.startswith(b'\xff\xd8\xff') or suffix=='.webp' and head[:4]==b'RIFF' and head[8:12]==b'WEBP' or suffix=='.webm' and head[:4]==b'\x1aE\xdf\xa3' or suffix=='.mp4' and head[4:8]==b'ftyp')
            if not valid:raise ValueError('Os bytes recebidos não correspondem ao formato informado.')
            temporary.replace(target)
        finally:temporary.unlink(missing_ok=True)
        return {'name':target.name,'size':size,'sha256':sha.hexdigest(),'mime':mimetypes.guess_type(target.name)[0] or 'application/octet-stream','index':index}
    def resume(self,identifier):
        with self.lock:
            job=self.jobs.get(identifier)
            if not job or job.get('status') not in ('interrupted','failed') or not job.get('prompt_id'):raise ValueError('Este trabalho não pode ser recuperado pelo histórico.')
            if self.running:raise ValueError('Aguarde o trabalho em andamento.')
            if job.get('engine_port')!=self.port:raise ValueError('Configure a mesma porta usada nesse trabalho antes de recuperar.')
            self.running=identifier;job.update(status='running',message='Consultando o histórico sem reenviar o prompt.');self.save()
            threading.Thread(target=self.run,args=(identifier,None),daemon=True).start();return copy.deepcopy(job)
    def cancel_engine(self,prompt_id):
        try:
            self.request('/api/jobs/'+urllib.parse.quote(prompt_id,safe='')+'/cancel',{})
            return 'Cancelamento solicitado ao motor para este trabalho.'
        except ValueError:
            self.request('/queue',{'delete':[prompt_id]})
            return 'Retirado da fila quando possível. Motores antigos podem continuar o processamento já iniciado; nenhum outro trabalho foi interrompido.'
    def cancel(self,identifier):
        with self.lock:
            job=self.jobs.get(identifier)
            if not job:raise ValueError('Trabalho não encontrado.')
            if job['status'] not in ('queued','running'):return copy.deepcopy(job)
            prompt_id=job.get('prompt_id')
            message=self.cancel_engine(prompt_id) if prompt_id else 'Cancelamento registrado antes da confirmação do motor.'
            job.update(status='cancelled',message=message,finished=time.time());self.save();return copy.deepcopy(job)
    def file(self,identifier,index):
        with self.lock:
            job=self.jobs.get(identifier)
            if not job or job.get('status')!='completed' or type(index) is not int or not 0<=index<len(job['outputs']):raise ValueError('Arquivo não encontrado.')
            name=job['outputs'][index]['name'];path=self.root/name
            if path.parent!=self.root or not path.is_file():raise ValueError('Arquivo não disponível.')
            return path,copy.deepcopy(job['outputs'][index])


def re_uuid(value):
    try:return isinstance(value,str) and str(uuid.UUID(value))==value
    except ValueError:return False

_SERVICE_LOCK=threading.Lock()
def service(server):
    with _SERVICE_LOCK:
        if not hasattr(server,'media_ai'):server.media_ai=MediaService()
        return server.media_ai
