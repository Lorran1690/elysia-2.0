# Elysia Desktop 2.1

Aplicativo desktop Tauri 2 para Windows 10/11 x64. Interface React 18 e TypeScript,
compilada com Vite e estilizada com Tailwind. Esta janela usa o WebView2 do Windows;
não abre Edge em modo app ou uma aba do navegador. Tauri, como outras tecnologias
desktop modernas, renderiza a interface usando um motor web integrado.

Baixe o `Elysia-Setup-x64.exe` da Release nativa. Feche a Elysia anterior antes de
instalar. O instalador atualiza a mesma pasta `%LOCALAPPDATA%\Programs\Elysia` e
mantém o diretório privado `%LOCALAPPDATA%\Elysia`. Necessita WebView2 Runtime e o
redistribuível Visual C++ v14 x64 disponíveis no Windows. Não instala drivers/CUDA.

## Interface

Quatro áreas: Conversas; Biblioteca; Criação (IA, composição/áudio, cinema e prévia);
Desenvolvimento (editor, utilitários e análise). Cada ferramenta fica em uma aba,
sem os menus internos duplicados do lançador anterior. Configurações possuem oito
categorias, temas claro/escuro/sistema, destaque, espaçamento, texto, atalhos,
contraste, foco, controle do histórico, arquivos privados, diagnóstico e som.

Três faixas instrumentais originais de 48 segundos, em repetição, com volume,
seleção, pausa, redução durante respostas e pausa ao ocultar a janela. Arquivos
pessoais podem ser adicionados à sessão. Não há reprodução automática ao iniciar.
O visualizador musical usa Three.js e React Three Fiber; GSAP anima somente painéis.

Avatar, rig, orbe e PNGs originais são compilados sem alteração dos arquivos fonte.
Nenhuma modelagem no Blender ou animação do avatar foi refeita nesta atualização.
O ícone foi gerado como proposta, mostrado e aprovado pelo proprietário antes da
inclusão. A fonte aprovada está em `branding/elysia-approved.png`.

## Dados e recursos nativos

Rust inicia somente o core Python incluído e o encerra ao fechar a janela. Se outra
Elysia ocupa a porta, a interface informa o conflito. A ponte aceita somente rotas
API explícitas para 127.0.0.1; não expõe shell, SQL ou leitura arbitrária de arquivos.
Conversas e preferências ficam em SQLite privado (`interface.sqlite3`). A biblioteca
continua no Vault anterior. Arquivos escolhidos para exportação usam diálogos
nativos. A pasta para gravação é autorizada pelo usuário por sessão; arquivos
existentes não são sobrescritos automaticamente.

Backups de conversas do aplicativo anterior podem ser importados em Dados e
privacidade. Não há migração automática do perfil de navegador antigo para o novo
WebView2. Exporte o histórico anterior antes de desinstalar a versão antiga.
Preferências de aparência existentes no armazenamento da mesma origem são lidas;
cores, amostragem e rig do avatar não são substituídos pelas cores da interface.

Esta atualização não altera o Neural Core, treinamento, geração por IA ou capacidade
linguística. O core próprio continua experimental; Voice Core pausado. ComfyUI,
modelos de imagem/vídeo e FFmpeg externo continuam com os requisitos anteriores.
Não há sincronização automática no Drive ou envio de conversas ao GitHub.

## Desenvolvimento e reprodução

`npm ci`, `npm run build` e `npm test` nesta pasta. Para a prévia de interface use
`npm run dev`; o backend real precisa estar em 127.0.0.1:8765. A fixture
`scripts/dev-backend.py` tem respostas sintéticas e serve somente a testes de UI.
`npm run tauri -- build --no-bundle` compila Rust; monte `core/Elysia.exe` e `_internal`
ao lado do EXE nativo usando o workflow `native-desktop.yml`.

O build verifica tipos, preferências, Rust, instalação, execução no WebView2 real,
reprodução de áudio, histórico SQLite, biblioteca, composição e ferramentas.
Os testes não medem inteligência nem realismo de vídeo.
