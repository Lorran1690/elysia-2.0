# Imagens e vídeos por modelos de IA

No EXE, abra **Imagens e vídeos por IA**. É um caminho distinto das composições
Canvas e do Cinema 3D. O aplicativo inclui os controles e o adaptador; **não inclui
ComfyUI, checkpoints nem uma GPU**. Um motor ComfyUI iniciado pelo usuário é
necessário para gerar. Sem ele, o painel mostra indisponibilidade; não substitui
uma falha por imagem procedural ou por amostra de demonstração.

## Uso

1. Instale/inicie o ComfyUI conforme sua documentação oficial, em
   `127.0.0.1:8188`, com os modelos que você tem direito de usar.
2. Na Elysia, diagnostique a porta e escolha os modelos já instalados.
3. Descreva a cena; selecione resolução, seed, passos e CFG.
4. Gere, acompanhe o trabalho e abra o resultado recebido do motor.
5. Baixe a imagem/vídeo e exporte os metadados. A opção de pasta do Drive usa
   o mesmo mecanismo local do Media Studio; sincronização precisa ser confirmada
   no cliente do Drive. Não há upload OAuth direto ao Drive dentro do EXE.

O adaptador aceita apenas loopback IPv4 e uma porta explicitamente escolhida.
Por escolha do proprietário, a geração fica no próprio computador, mesmo com
mais demora e limitações. O aplicativo não cria túneis, não contrata GPU e não
aceita URLs remotas. O motor local recebe as descrições e os parâmetros.
O envio de resultados ao Drive é uma operação separada de backup.

### Imagens

Fluxo fixo: CheckpointLoaderSimple, CLIPTextEncode, EmptyLatentImage, KSampler,
VAEDecode, SaveImage. Destinado a checkpoints completos compatíveis com SD 1.5
ou SDXL. Outros modelos com carregadores diferentes não são suportados por esse
fluxo. Imagens: até 1,5 megapixel, um resultado por trabalho. Comece em 512 px
quando houver pouca memória. Checkpoints SDXL precisam de mais recursos.

Direção visual acrescenta termos de fotografia ou cinema à descrição; não é
planejamento por um LLM e não traduz textos. O próprio modelo de mídia produz
os pixels. Ao trocar o checkpoint, nomes contendo Turbo/Lightning recebem um
ponto de partida de 4 passos/CFG 1; outros, 20 passos/CFG 6. Consulte o modelo:
o nome é só uma heurística inicial, não uma identificação técnica confiável.

### Vídeos — experimental

Fluxo nativo de **texto para vídeo Wan 2.1** com UNETLoader, CLIPLoader (UMT5),
VAELoader, EmptyHunyuanLatentVideo, ModelSamplingSD3, KSampler, VAEDecode e
SaveWEBM. Não há imagem de entrada, sequência de slides ou interpolação que
simule movimento neural. O modelo precisa produzir os quadros.

Referência inicial: `wan2.1_t2v_1.3B_fp16.safetensors`,
`umt5_xxl_fp8_e4m3fn_scaled.safetensors` e `wan_2.1_vae.safetensors`. Nomes de
arquivo não comprovam compatibilidade ou licença. Use pesos oficiais ou modelos
compatíveis cuja licença você verificou. O diagnóstico lista nós e arquivos;
não executa um benchmark nem garante memória suficiente.

O painel oferece 384×256, 512×288, 832×480 ou 1280×720, 17/33/49/65/81 quadros a 16 fps
(aproximadamente 1 a 5 segundos). A disponibilidade de 720p no controle não é
prova de qualidade ou de viabilidade no hardware. **Este fluxo ainda não teve
uma geração neural de vídeo real validada nesta entrega.** Não gera um minuto
contínuo, não faz concatenação de clipes e não adiciona áudio. O Cinema 3D com
trilha continua sendo outro recurso. O perfil inicial de 384×256/17 quadros reduz memória; mesmo assim,
o funcionamento na GTX 1650 de 4 GB não foi validado. ComfyUI pode precisar
de offload para RAM/CPU e levar bastante tempo. A escolha local é respeitada;
não há fallback para um serviço remoto. 720p e um minuto neural contínuo
permanecem objetivos não atingidos neste fluxo.

## Eficiência, estado e privacidade

- Um trabalho por vez no aplicativo, batch 1; o ComfyUI administra seu cache de
  modelos e memória. A Elysia não força descarregamento entre gerações.
- Mesmo motor/porta, parâmetros e seed reutilizam trabalho ativo ou concluído.
  Mude a seed para criar uma variação. Isso evita cálculos repetidos; não é uma
  medição de aceleração do modelo.
- Polling de histórico; sem percentuais ou estimativas de tempo inventados.
- Cancelamento pelo endpoint atômico por ID do ComfyUI recente. Em versões
  antigas, só remove da fila quando possível; processamento já iniciado pode
  continuar. Nunca chama interrupção global de outros trabalhos.
- Estado privado em `%LOCALAPPDATA%\Elysia\media-ai` no Windows. Prompts e
  metadados não são criptografados. A interface mostra os 20 trabalhos mais
  recentes. Arquivos antigos não são apagados automaticamente.
- Ao reiniciar, trabalhos incompletos aparecem interrompidos. Recuperação consulta
  o mesmo prompt_id, na mesma porta, sem reenviar o prompt. Falha de conexão não
  significa que o motor parou; consulte seu histórico antes de repetir.
- Arquivos são recebidos do endpoint `/view`, com caminhos limitados, tamanho e
  assinatura de formato verificados. Hash SHA256 do resultado é registrado.
  Isso não mede realismo, correção anatômica ou qualidade cinematográfica.
- Metadados incluem descrição efetiva, modelos por nome, seed, parâmetros e
  tempos. Hash dos pesos não é fornecido pelo protocolo e fica não informado;
  a reprodução entre instalações depende também dos pesos/versões utilizados.
- Não há importação de workflows arbitrários ou instalação automática de nós.
  O aplicativo não inclui nem redistribui código ComfyUI (GPL-3.0).

## Referências e testes

[API oficial](https://docs.comfy.org/development/comfyui-server/comms_routes),
[fluxo Wan oficial](https://comfyanonymous.github.io/ComfyUI_examples/wan/),
[requisitos do ComfyUI](https://docs.comfy.org/installation/system_requirements).

Os testes automatizados de protocolo e navegador usam um motor **simulado** e
uma imagem de um pixel. Verificam conexão, graph, download, cache, parâmetros e
cancelamento; não avaliam qualidade neural. A execução Windows exige passar por
esse fluxo no EXE real antes da publicação. Testes reais com modelos de imagem
são registrados separadamente, com origem dos pesos e resultado observado.
Neural Core próprio permanece inalterado e Voice Core pausado.
