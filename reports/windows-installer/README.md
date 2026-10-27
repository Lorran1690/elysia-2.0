# Instalador Windows por usuário

`Elysia-Setup-x64.exe` instala o aplicativo em
`%LOCALAPPDATA%\Programs\Elysia`, com entrada no menu Iniciar, atalho opcional na
área de trabalho e registro de desinstalação por usuário. O AppId é estável para
reutilizar a instalação em atualizações. A versão portátil continua disponível.

O instalador contém o mesmo diretório PyInstaller validado pelo workflow Windows:
interface v11, núcleo próprio, pesos, tokenizer e módulos locais. Não inclui
ComfyUI, seus modelos externos, CUDA ou drivers. Requer o redistribuível Visual C++
v14 x64; não baixa ou executa outros instaladores.

Os arquivos privados em `%LOCALAPPDATA%\Elysia` ficam fora da pasta do programa.
Não há regra de exclusão recursiva de dados privados no desinstalador. Conversas e
preferências continuam no armazenamento do navegador; backups privados externos
continuam necessários. A instalação não configura Drive nem altera o treinamento.

O script `scripts/test-installer-windows.py` executa o instalador real no Windows,
usa uma pasta com espaços e acentos, verifica o registro HKCU e o atalho, inicia o
EXE instalado com o checkpoint real, reinstala, desinstala e confere arquivos
privados de controle fora da pasta do programa. Esse teste não mede a qualidade
da conversa. A limpeza aguarda o helper temporário do Inno liberar o log após a
remoção; as verificações do produto não são ignoradas.

O workflow publica o instalador somente depois dessas verificações e registra seu
SHA-256. Consulte `release-verification.json` para identificar o pacote validado.
