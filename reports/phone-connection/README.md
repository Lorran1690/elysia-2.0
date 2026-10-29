# Android como cliente do computador

Implementação: `4bd969dfe6122186d854edccef5230ed816c0a33`.
[Configuração do computador e telefone](../../desktop/PHONE-CONNECTION.md).

O gateway autenticado reutiliza o Neural Core próprio e o serviço ComfyUI do
computador. Só expõe conversa, saúde e operações de geração; a biblioteca privada
do computador, arquivos estáticos e ferramentas administrativas não são expostos.
A chave fica apenas na memória da sessão no Android, fora dos backups.

## Verificação

- Três testes Python usando socket HTTP real: autenticação inválida/origem
  indevida não chama o modelo, biblioteca inacessível e preflight restrito.
- Teste TypeScript: endereço HTTPS, bloqueio de redirecionamento e cookies,
  operações permitidas, desconexão revoga a sessão.
- Suite frontend e compilação Android aprovadas localmente.
- [Navegador com núcleo real](browser-real-core.json): interface móvel 390×844,
  configuração, resposta não vazia do checkpoint próprio através de socket HTTPS,
  acompanhamento do serviço de geração e ocultação do compositor ao desconectar.
  [Captura da conversa](real-core-conversation.png) usa uma mensagem sintética.

Reprodução do teste integrado: compilar `desktop` no modo Android e executar
`python scripts/test-phone-computer.py` no ambiente PyTorch/Playwright. O script
usa Chromium em `/usr/bin/chromium` ou `ELYSIA_CHROMIUM_PATH` e certificados
transitórios fora do Git. Para isolar o transporte no navegador, aceita o
certificado autoassinado e desabilita a exigência de permissão de rede local
somente nesse processo de teste. O aplicativo de produção exige HTTPS confiável;
este teste não substitui validação de VPN/permissões no telefone real.

A resposta ainda é imprecisa e repetitiva. O teste comprova comunicação e uso do
modelo próprio, sem demonstrar melhoria conversacional. Não houve geração por GPU
nem avaliação de vídeo realista. Não houve conexão ao computador ou telefone do
proprietário. O gateway precisa ser iniciado no computador, com túnel HTTPS
privado e ComfyUI/modelos instalados para a geração por IA.

A compilação de um novo APK e executável Windows é registrada no GitHub Actions.
O APK de build 15 está publicado e assinado com a chave persistente. A assinatura,
identidade, hash e validação instalada de produção passaram.
Os dois testes debug anteriores pararam antes da instalação, na inicialização
do emulador (ANR do HOME na primeira tentativa e prontidão na segunda).

## Encaminhamento privado com Tailscale

Depois de instalar e conectar Tailscale no computador e Android à sua rede
privada, deixe o gateway aberto e execute em outro PowerShell:

```powershell
tailscale serve --bg localhost:8766
tailscale serve status
```

Use no aplicativo o endereço HTTPS mostrado por Serve, sem caminho adicional.
O comando pode pedir habilitação de HTTPS/DNS na sua rede privada. A conta e esse
passo dependem do proprietário. Copie a chave diretamente do arquivo privado no
computador para o campo de senha do telefone; não envie a chave nesta conversa.

Esses comandos foram conferidos na [documentação oficial de Serve](https://tailscale.com/docs/reference/tailscale-cli/serve),
consultada em 29/10/2026. Serve limita o acesso à tailnet e faz a terminação TLS;
o processo Elysia permanece no loopback. A opção `--bg` mantém o encaminhamento
ativo em segundo plano; o gateway e o computador também precisam continuar
ligados. Não foi configurado Tailscale nem executado esse comando no computador
do proprietário.

O gateway mantém o histórico de geração em `phone-media-ai`, separado de
`media-ai` do processo desktop, para evitar escritas concorrentes nos mesmos
arquivos de estado. Os dois usam o ComfyUI do computador.

APK build 15: SHA-256 `0a0e36a9f8aef616efee9f9ced8066b7172774d0d6b9acc8105140f417d47b33`,
11.390.489 bytes, origem do aplicativo `4bd969dfe6122186d854edccef5230ed816c0a33`.
[Verificação estática do pacote](package-verification.json). Os artefatos unsigned
das tentativas 1 e 2 do workflow 40969592957 têm APKs idênticos em bytes.

## APK debug instalado aprovado

A [execução 40971821286](https://github.com/Lorran1690/elysia-2.0/actions/runs/40971821286)
passou em Android 15/API35, sem rede: biblioteca e backups, ferramentas, editor,
áudio, PNG/exportação nativa, teclado real e rotação, sem erros JavaScript.
[Relatório](debug-apk/device-verification.json) e [proveniência](debug-apk/provenance.json).
O código da aplicação corresponde ao build público 15; a identidade do debug é
diferente e ele permite CDP. Isso não é prova de execução do modelo no telefone.

## APK assinado de produção aprovado

A [execução 40972407084, tentativa 1](https://github.com/Lorran1690/elysia-2.0/actions/runs/40972407084/attempts/1)
passou com o próprio APK público build 15, em imagem Android `user`,
`ro.debuggable=0`, sem socket de depuração e sem CDP. Verificou abertura,
presença central, título e conteúdo de nota sintética após reinstalação por cima
e retrato/paisagem 1080×2340/2340×1080.
[Relatório](signed-apk/device-verification.json), [origem e hashes](signed-apk/provenance.json),
[biblioteca preservada](signed-apk/release-reinstalled-library.png).

O código, APK, instalador Windows e evidências estão publicados. A etapa restante
no equipamento do proprietário é iniciar o gateway e configurar o HTTPS privado
na VPN. A conversa pelo modelo real foi avaliada no navegador com transporte
HTTPS; a geração por GPU e a ligação entre os aparelhos do proprietário não foram
executadas nesta sessão.
