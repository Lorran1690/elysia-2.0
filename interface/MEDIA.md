# Criação de mídia e editor de código

## Capacidades implementadas

- **Imagem:** composição em Canvas com título, subtítulo, cores, três estilos e
  imagem de fundo opcional. Exportação PNG em 640×360, 1280×720, 1920×1080, 1080×1920 ou 720×720.
- **Áudio:** síntese de tons e sequências de notas em WAV PCM de 16 bits, mono,
  22.050 Hz. Ondas senoidal, triangular e quadrada; volume limitado e envelope
  para suavizar os ataques. Máximo de 30 segundos. Não há fala ou clonagem de voz.
- **Vídeo:** animação da composição em WebM com preferência por VP9 e fallback VP8/WebM suportado pelo
  navegador; 24, 30 ou 60 quadros/s solicitados, por 2 a 60 segundos, até Full HD
  horizontal ou vertical. Taxa de bits proporcional à resolução e fluidez, de
  2,5 a 24 Mbit/s (Full HD/60 solicita aproximadamente 19,9 Mbit/s).
  A exportação é em tempo real: o navegador pode entregar menos quadros em
  computadores ocupados. Recomenda-se começar em 720p/30. A gravação usa o
  relógio de animação do navegador, sem reinicializar o Canvas a cada quadro. Vídeo sem trilha sonora.
  A janela deve permanecer visível durante a gravação; é possível cancelar.
- **Projeto editável:** exportação e restauração de JSON com os controles e uma
  cópia reduzida da imagem de fundo. A imagem original não é alterada. Escolha
  imagens PNG/JPEG/WebP de até 8 MB e até 16 milhões de pixels.
- **Código:** editor com rascunho no navegador e download de Python, JavaScript,
  HTML, CSS e JSON. Modelos iniciais determinísticos e validação sintática de
  Python e JSON. A validação não executa o programa nem comprova sua correção.
  A prévia HTML tem sandbox, política de conteúdo restrita e remoção de scripts,
  redirecionamentos, links ativos, formulários e conteúdo externo.

Esses recursos são composição gráfica, síntese musical e estruturas iniciais de
código. **Não são modelos de IA generativa**: não criam cenas fotorrealistas de um
prompt, filmes com personagens, fala ou programas arbitrários por linguagem
natural. Os modelos de mídia por IA ainda não estão integrados. O Transformer
linguístico próprio e seus pesos continuam os mesmos. Voice Core permanece pausado.

## Armazenamento privado no Google Drive

O Google Drive é o destino dos arquivos, não o mecanismo de geração. A conexão
Google Drive disponível no chat não fornece credenciais ao aplicativo instalado.

O aplicativo oferece:

1. Baixar o arquivo e enviá-lo manualmente à pasta privada do Drive.
2. Selecionar uma pasta do **Google Drive para computador** usando o seletor do
   Edge/Chrome. A seleção é lembrada no navegador quando permitido.
3. Gravar o arquivo gerado nessa pasta e, opcionalmente, ativar a gravação dos
   próximos arquivos da sessão. A permissão de escrita continua sob controle do
   navegador. Se já houver arquivo com o mesmo nome, a operação é recusada.

Selecionar uma pasta comum salva somente localmente. Mesmo em uma pasta do Drive,
o aplicativo confirma **a gravação local**, não a conclusão da sincronização.
Confirme o envio no cliente Google Drive para computador ou no site do Drive.
Não há upload direto por API/OAuth dentro do EXE nesta versão. O modo automático
só atua enquanto o painel estiver aberto e a pasta tiver permissão de escrita.

A pasta privada do proprietário é informada no chat, sem gravar seu identificador
ou URL pessoal no repositório público. Os arquivos demonstrativos enviados pelo
conector do chat são diferentes da sincronização pelo aplicativo; o teste desta
última usa um diretório simulado e não comprova upload automático à nuvem.

Os projetos JSON, imagens e códigos editados podem conter dados pessoais. Não
são enviados automaticamente ao GitHub nem usados para treinar o núcleo. Salve os
arquivos antes de fechar o painel. O backup do projeto de mídia é separado dos
arquivos exportados, das conversas e do Knowledge Vault.

## Verificação e referências

Os testes verificam cabeçalho e dimensões de PNG, estrutura e duração de WAV,
decodificação de WebM no navegador, cancelamento, restauração de projeto, gravação
simulada em pasta, colisões e permissões, exportação de código e isolamento da
prévia HTML. A compilação Windows só é publicada após passar pelos testes do
executável e do navegador.

Referências consultadas: [Canvas captureStream](https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/captureStream)
e [MediaRecorder.isTypeSupported](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder/isTypeSupported_static).
A verificação de codec não garante recursos suficientes para gravar: o aplicativo
mostra erro se a codificação falhar. Os recursos de criação não requerem câmera,
microfone, serviço pago ou uma conexão com a internet.

## Apresentação da Elysia

No painel Vídeo, o botão **Apresentação da Elysia · 1 minuto · 720p** carrega
um roteiro de seis cenas, com textos sobre os módulos, progresso, transições
e animação de identidade visual. O roteiro identifica o núcleo neural como pesquisa.
O título/subtítulo e a imagem de fundo dos outros estilos não alteram esse roteiro.
No aplicativo, a exportação continua WebM em tempo real e sem áudio.

Para renderizar cada um dos 1.800 quadros sem depender da velocidade de captura
em tempo real, o projeto inclui `scripts/render-presentation.py`. Esse caminho
requer Python com Playwright/Chromium e ffmpeg instalados; não está embutido no EXE.
Ele produz MP4 H.264, 30 fps constantes, 60 segundos, 720p ou 1080p, sem áudio:

```sh
python scripts/render-presentation.py --output Elysia-apresentacao.mp4 --height 720
```

A renderização usa o mesmo roteiro e o mesmo desenho Canvas do aplicativo.
Não há geração de cenas por modelo de IA, música ou fala neste vídeo.

## Cinema 3D contínuo com trilha

O painel Vídeo agora oferece **Cinema 3D · cena contínua com trilha**. Abre um
ambiente 3D com avatar geométrico, núcleo em rotação, partículas em trânsito e
estações dos módulos. Uma câmera percorre o ambiente em um plano contínuo de
60 segundos: sem fotos, sequência de slides, cortes ou entrada de imagens/vídeos.
Os letreiros fazem parte do ambiente 3D. É animação procedural, não filmagem
fotorrealista ou geração por um modelo de vídeo por IA.

A página permite reproduzir com trilha instrumental sintetizada, gerar WebM
com áudio estéreo e baixar. Não usa câmera, microfone, gravações ou Voice Core.
A aba precisa ficar visível; a gravação é interrompida ao ocultá-la. Sua
fluidez depende do computador, pois a captura no navegador é em tempo real.
Os controles de título dos estilos antigos não editam esse ambiente.

Para produção em **MP4 H.264/AAC, 1280×720, 30 fps e 60 segundos**, o script
abaixo renderiza cada instante da cena 3D e monta o vídeo com uma trilha original
sintetizada de 80 BPM, estéreo a 48 kHz. Não usa imagens estáticas como cenas:
JPEG é apenas o transporte interno dos quadros renderizados ao codificador.
É possível terminar a renderização mais lentamente que a reprodução sem perder
quadros. Os scripts precisam de NumPy, Playwright/Chromium e ffmpeg/ffprobe
instalados; a produção MP4 não está embutida no executável Windows.

```sh
python scripts/render-continuous.py --output /caminho/privado/Elysia-filme-3D-60s-720p.mp4
python scripts/verify-continuous.py /caminho/privado/Elysia-filme-3D-60s-720p.mp4 --report /caminho/privado/verificacao.json
```

A verificação exige 1.800 quadros decodificados, duração de um minuto, áudio
estéreo audível sem pico saturado, e ausência de intervalos congelados ou pretos
de meio segundo. A continuidade da câmera e a ausência de imagens de entrada
são também verificáveis no código. O destino privado das mídias é o Drive;
as credenciais e os identificadores da pasta não fazem parte do projeto.
