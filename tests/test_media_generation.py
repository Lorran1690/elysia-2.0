"""Protocol tests use a simulated ComfyUI, not neural quality evaluations."""
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from actions.media_generation import MediaService,validate_request,workflow,IMAGE_NODES,VIDEO_NODES

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6N1YAAAAASUVORK5CYII=')
PARAMS={'kind':'image','prompt':'synthetic protocol fixture','negative':'blur','checkpoint':'fixture.safetensors','width':512,'height':512,'steps':20,'seed':7,'cfg':6}

@pytest.fixture
def motor(tmp_path):
    state={'posts':[],'hold':False,'delay':0,'failed':False,'unsafe':False}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,data):
            body=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path=='/system_stats':return self.send({'devices':[{'name':'SIMULATED CPU','type':'cpu'}]})
            if self.path.startswith('/object_info/'):
                name=self.path.rsplit('/',1)[-1];keys={'CheckpointLoaderSimple':'ckpt_name','UNETLoader':'unet_name','CLIPLoader':'clip_name','VAELoader':'vae_name'}
                inputs={keys[name]:[['fixture.safetensors']]} if name in keys else {}
                return self.send({name:{'input':{'required':inputs}}})
            if self.path.startswith('/history/'):
                if state['hold']:return self.send({})
                return self.send({'fixture-id':{'status':{'completed':True,'status_str':'error' if state['failed'] else 'success'},'outputs':{'7':{'images':[{'filename':'../unsafe.png' if state['unsafe'] else 'fixture.png','subfolder':'','type':'output'}]}}}})
            if self.path.startswith('/view?'):
                self.send_response(200);self.end_headers();self.wfile.write(PNG);return
            self.send({})
        def do_POST(self):
            data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))));state['posts'].append((self.path,data))
            if self.path=='/prompt':time.sleep(state['delay']);return self.send({'prompt_id':'fixture-id'})
            self.send({'cancelled':True})
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    service=MediaService(tmp_path);service.probe(server.server_port)
    yield service,state
    if service.running:service.cancel(service.running)
    deadline=time.monotonic()+5
    while service.running and time.monotonic()<deadline:time.sleep(.05)
    server.shutdown();server.server_close();thread.join()


def wait(service,identifier):
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        job=next(j for j in service.list()['jobs'] if j['id']==identifier)
        if job['status'] in ('completed','failed','cancelled'):return job
        time.sleep(.05)
    raise AssertionError('Protocol test timed out')


def test_real_protocol_shape_download_cache_and_persistence(motor):
    service,state=motor
    first=service.submit(PARAMS)['job'];job=wait(service,first['id']);assert job['status']=='completed'
    path,metadata=service.file(job['id'],0);assert path.read_bytes()==PNG and metadata['size']==len(PNG)
    result=service.submit(PARAMS);assert result['reused'] and result['job']['id']==job['id']
    assert len([p for p in state['posts'] if p[0]=='/prompt'])==1
    assert MediaService(service.root).list()['jobs'][0]['status']=='completed'
    graph=next(p[1]['prompt'] for p in state['posts'] if p[0]=='/prompt')
    assert graph['4']['inputs']['batch_size']==1 and graph['5']['inputs']['seed']==7
    with pytest.raises(ValueError):service.file('../x',0)


def test_cancellation_race_only_targets_own_prompt(motor):
    service,state=motor;state.update(hold=True,delay=.2)
    job=service.submit(PARAMS)['job'];service.cancel(job['id'])
    time.sleep(.5)
    assert wait(service,job['id'])['status']=='cancelled'
    assert any(p[0]=='/api/jobs/fixture-id/cancel' for p in state['posts'])
    assert not any(p[0]=='/interrupt' for p in state['posts'])


def test_motor_errors_and_path_traversal_are_not_outputs(motor):
    service,state=motor;state['unsafe']=True
    first=service.submit(PARAMS)['job'];assert wait(service,first['id'])['status']=='failed'
    assert not list(service.root.glob('*.png'))
    state.update(unsafe=False,failed=True)
    second=service.submit({**PARAMS,'seed':8})['job'];assert wait(service,second['id'])['status']=='failed'


def test_text_to_video_graph_is_neural_latent_workflow_not_images():
    p=validate_request({'kind':'video','prompt':'single continuous live action scene','diffusion_model':'wan.safetensors','text_encoder':'umt5.safetensors','vae':'wan_vae.safetensors','width':1280,'height':720,'frames':81,'fps':16})
    graph,effective=workflow(p,'Elysia/test')
    assert graph['6']['class_type']=='EmptyHunyuanLatentVideo'
    assert graph['6']['inputs']['length']==81 and graph['10']['class_type']=='SaveWEBM'
    assert not any(n['class_type']=='LoadImage' for n in graph.values())
    for patch in [{'width':99999},{'frames':82},{'seed':True},{'cfg':float('nan')},{'kind':'arbitrary'}]:
        with pytest.raises(ValueError):validate_request({**p,**patch})
    assert set(n['class_type'] for n in graph.values())<=set(VIDEO_NODES)
