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
O APK público de build 7 ainda é a versão anterior até a publicação do novo pacote.
