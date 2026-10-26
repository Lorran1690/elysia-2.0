# Aplicativo Elysia para Windows

## Abrir o aplicativo

Na página de Releases do repositório, baixe `Elysia-Windows-x64.zip` da versão
desejada. Extraia **a pasta inteira** e abra `Elysia.exe`. Não mova apenas o EXE:
a pasta `_internal` contém o núcleo, os pesos, a interface e o Python incluídos.
O Microsoft Visual C++ v14 x64 redistribuível deve estar instalado.

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
SHA-256 para verificar o ZIP. O artefato temporário do Actions dura 90 dias;
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
