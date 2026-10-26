# Aplicativo Elysia para Windows

## Instalar no computador

Na [versão Windows desejada em Releases](https://github.com/Lorran1690/elysia-2.0/releases),
baixe **`Elysia-Setup-x64.exe`**, abra o arquivo e siga **Avançar → Instalar**.
O instalador em português instala a Elysia para o usuário atual, por padrão em
`%LOCALAPPDATA%\Programs\Elysia`, cria uma entrada no menu Iniciar e oferece
atalho opcional na área de trabalho. Não precisa extrair ZIP nem instalar Python.

Para atualizar, feche a Elysia e execute o instalador da versão nova. O instalador
reutiliza a pasta da instalação anterior. A interface v11 e todos os módulos do
pacote portátil também estão no instalador. Modelos externos e ComfyUI continuam
sendo instalados separadamente para geração por IA.

Para remover, use **Configurações do Windows → Aplicativos → Elysia → Desinstalar**.
A biblioteca e as mídias privadas em `%LOCALAPPDATA%\Elysia` são preservadas durante
atualização e desinstalação; histórico e preferências continuam no navegador. Isso
não substitui backup externo. O instalador não configura sincronização no Drive.

Requer Windows 10/11 x64 e Microsoft Visual C++ v14 x64 redistribuível. O instalador
não tem assinatura digital e não exige administrador. Não instala drivers nem CUDA.

## Alternativa portátil

Baixe `Elysia-Windows-x64.zip`, extraia **a pasta inteira** e abra `Elysia.exe`.
Não mova apenas o EXE: `_internal` contém os recursos necessários.

O lançador abre a interface no modo aplicativo do Microsoft Edge quando encontrado;
caso contrário, usa o navegador padrão. Mantenha o lançador aberto e use **Encerrar
Elysia** para desligar o núcleo. Não precisa digitar comandos, instalar Python ou CUDA.
A inferência usa CPU e a porta local 8765. Feche outra Elysia antes de abrir.
O executável é experimental e não tem assinatura digital. Não requer administrador.

Se estiver usando o código clonado com `.venv` já instalada, dê dois cliques em
`Elysia.cmd` na raiz do projeto. É uma alternativa ao pacote completo.

## Preservação e recuperação

Código, pesos do modelo, tokenizer, datasets preparados e documentação são
versionados no GitHub. Cada pacote gerado pelo workflow `Windows desktop app`
é testado com o checkpoint real e preservado em uma **GitHub Release**, com
SHA-256 para verificar o ZIP e o instalador. O artefato temporário do Actions dura 90 dias;
a Release guarda a cópia distribuível além desse prazo.

A conversa atual é salva no armazenamento do navegador após cada resposta
concluída. Ao reabrir a mesma origem e o mesmo perfil, ela é restaurada. Esse
armazenamento pode ser apagado ao limpar dados do navegador, trocar de perfil ou
formatar o computador. **Não é um backup externo.**

Use **Exportar backup**, guarde o JSON em armazenamento privado fora do computador
e use **Restaurar backup** após reinstalar. Importar substitui a conversa atual;
exporte antes se quiser preservá-la. **Nova conversa** limpa a conversa atual.
Conversas e preferências pessoais não são publicadas automaticamente no GitHub.
O pacote baixado também não envia código ou arquivos locais ao GitHub.

O Git preserva os arquivos efetivamente enviados. Novos treinamentos executados
na sua máquina precisam ter seus resultados enviados para também ficarem protegidos;
a instalação do aplicativo não sincroniza esses arquivos automaticamente.

## Reproduzir o pacote

O workflow `.github/workflows/desktop.yml` usa Windows, Python 3.12, PyTorch CPU
2.11.0 e PyInstaller 6.16.0. Inclui somente a interface, o checkpoint SFT próprio
e seu tokenizer; dados pessoais e caches de treinamento não entram no pacote.
O teste `Elysia.exe --smoke-test desktop-smoke.json` verifica o executável congelado,
seus recursos locais e uma resposta do modelo real. Isso não mede inteligência.
O teste automatizado não abre a janela gráfica do usuário.

## Biblioteca, ferramentas e mídia

Os novos módulos são descritos em [MODULES.md](MODULES.md), incluído no pacote.
A biblioteca fica em `%LOCALAPPDATA%\Elysia\vault.sqlite3`, fora da pasta do
aplicativo. Ao trocar de versão, preserve esse diretório. Exporte a biblioteca
pela interface para guardá-la em backup privado fora do computador. Reinstalar
ou formatar sem esse backup pode perder os registros; não há sincronização remota
automática. Conversas e biblioteca têm backups separados.

As ferramentas de criação PNG, WAV, WebM, editor e destino no Drive são descritas
em [MEDIA.md](MEDIA.md), incluído no pacote.

O instalador é compilado com Inno Setup 6, usando `interface/installer/elysia.iss`.
O workflow instala o pacote em uma pasta com espaços e acentos, inicia o EXE
instalado com o modelo real, reinstala e desinstala, verificando o atalho, registro
por usuário e preservação de arquivos privados. O relatório acompanha a Release.
Referências: [instalação sem elevação](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm)
e [diretório de atualização](https://jrsoftware.org/ishelp/topic_setup_defaultdirname.htm).
