## Instalador Windows

Baixe `Elysia-Setup-x64.exe` para instalar a Elysia diretamente, sem extrair ZIP.
Inclui a interface v11 e todos os módulos existentes. Instala por usuário, oferece
atalho na área de trabalho e cria a entrada no menu Iniciar e na lista de aplicativos.
Atualização e desinstalação preservam os dados privados fora da pasta do programa.
Feche a Elysia antes de atualizar. O pacote portátil continua disponível.

O instalador não inclui ComfyUI nem modelos externos. Requer Windows 10/11 x64 e
o Microsoft Visual C++ v14 x64 redistribuível; não possui assinatura digital.

## Interface v11 integrada ao aplicativo

Avatar do pacote fornecido pelo proprietário: busto e corpo preservados, respiração,
movimento de cabeça e cabelo, aceno e controles de partículas, tamanho e enquadramento.
As preferências antigas são migradas. O aceno é visual; o Voice Core continua pausado.

Mantidos o Neural Core próprio experimental, conversa com backup, Knowledge Vault,
editor e ferramentas de código, bancada de análise, catálogo de habilidades,
Media Studio, cinema 3D com trilha e geração local por ComfyUI. A interface usa
bibliotecas locais e não depende de CDN. O ComfyUI e seus modelos continuam sendo
instalados separadamente; vídeos neurais realistas ainda não foram validados.

Extraia a pasta inteira do ZIP e abra Elysia.exe dentro dela, preservando `_internal`.
Os dados privados existentes não são substituídos pela atualização.

# Caminho de geração por modelos de mídia

Novo painel **Imagens e vídeos por IA** no EXE: diagnóstico de ComfyUI local,
modelos instalados, descrição de cena, seed, parâmetros, histórico privado,
reutilização de resultados e cancelamento por trabalho. Imagens SD 1.5/SDXL e
fluxo experimental de texto para vídeo Wan 2.1.

**ComfyUI, pesos e GPU não estão incluídos no EXE.** Inicie um motor compatível
e leia GENERATIVE-MEDIA.md. Vídeo neural real ainda não validado; clipes curtos
sem áudio nesse fluxo. Isso não é uma entrega de vídeos realistas de um minuto.
Neural Core e Voice Core não foram alterados.

---

# Bancada de análise e habilidades

Novos painéis no EXE: **Bancada de análise** e **Habilidades e evolução**.
Inspeção estática de arquivos (até 4 MB), estrutura/grafo Python, comparação de
versões, aceitar/desfazer no editor, projetos exportáveis e notas no Vault.
Catálogo com estados e limites das 21 áreas do memorando.

Fluxo inspirado na referência Eleven, com implementação própria. Não inclui
Ghidra/Rizin, decompilação ou agentes externos. Não executa os arquivos enviados
e não altera arquivos em disco. Exporte o projeto antes de fechar o painel.
Neural Core experimental; Voice Core continua pausado.

---

# Cinema 3D com trilha instrumental

No Media Studio, abra **Vídeo → Cinema 3D · cena contínua com trilha**.
Uma câmera percorre um ambiente geométrico com avatar, núcleo e módulos em
movimento durante 60 segundos, sem slides ou imagens estáticas de entrada.
Reproduza com música ou gere WebM com áudio estéreo em 1280×720.

Mantenha a aba visível durante a exportação. A captura do navegador é em tempo
real, com fluidez dependente do computador. O renderizador MP4 quadro a quadro
está no código-fonte e requer ferramentas de produção separadas. Não é geração
por IA de vídeo nem filmagem fotorrealista. Voice Core continua pausado.

---

Aplicativo experimental da Elysia para Windows x64.

Baixe Elysia-Windows-x64.zip, extraia toda a pasta e abra Elysia.exe.
O pacote inclui Python, PyTorch CPU, o Transformer próprio, seu tokenizer e a interface.
Não precisa instalar Python ou CUDA. Requer o Microsoft Visual C++ v14 x64
redistribuível e um navegador (Edge abre em modo de aplicativo).

O executável foi testado no Windows do GitHub Actions com o checkpoint real.
Ainda não foi validado no computador do proprietário. Não tem assinatura digital.
O modelo ainda responde de forma limitada e repetitiva. Voice Core pausado.

Código, pesos e materiais preparados estão preservados no Git. Conversas não
são enviadas automaticamente ao GitHub. Use Exportar backup e guarde o arquivo
em armazenamento privado fora do computador; Restaurar backup recupera a conversa.
Veja LEIA-ME.md no pacote para detalhes.

Novos módulos: Knowledge Vault com notas/documentos/fontes, busca e backup privado;
ferramentas locais de cálculo, JSON, texto e SHA-256; visualização de imagens,
áudio e vídeo locais. Nenhum documento pessoal é enviado ao GitHub ou usado no
treino. A biblioteca permanece independente do chat. Os pesos do núcleo não mudaram.

Criação local: exportação PNG de composições, WAV de tons e melodias, e WebM de
animações curtas sem áudio. Projeto editável com restauração e editor de código
com estruturas iniciais, download e validação de sintaxe. Integração por pasta
sincronizada do Google Drive para computador, com seleção e permissão do usuário.
Não há modelos de IA generativa de mídia ou upload direto por API no EXE.
Veja MEDIA.md para capacidades e limites.
