# Android · evidências históricas do build 7

[Baixar Elysia-Android.apk](https://raw.githubusercontent.com/Lorran1690/elysia-2.0/33c4e6145372fb71d157ba13b4744e9b562b5ea4/artifacts/android/Elysia-Android.apk) · [Guia de instalação e atualização](../../desktop/ANDROID.md)

APK histórico **2.2.0, compilação 7**, pacote `org.elysia.mobile`, com
11.386.393 bytes. Origem registrada no [manifesto histórico](https://github.com/Lorran1690/elysia-2.0/blob/33c4e6145372fb71d157ba13b4744e9b562b5ea4/artifacts/android/latest.json)
e na [proveniência](build-provenance.json):
`d44aab78a5cd66a4ace8f549a66704aef1c78686`.

SHA-256 do APK:
`d18b21062b157079dce47a7b61c378ba4e1eb80c4496f2a632928ade9e8f4529`.

A interface compartilha os componentes da edição Windows, com navegação por
toque, histórico recolhível, ajustes para telefone, teclado e rotação. A biblioteca
local usa IndexedDB; há ferramentas de texto, JSON e cálculo, composição PNG,
áudio e compartilhamento nativo. Android 7/API 24 ou superior, com Android System
WebView atualizado; os testes Android usam emulador Android 15/API 35.

## O que cada evidência comprova

| Camada | Resultado e alcance |
| --- | --- |
| [Navegador Chromium](browser-ui-verification.json) | Aprovado em cinco dimensões de tela, incluindo retrato e paisagem, fonte a 125%, navegação e armazenamento local. O teclado foi simulado; isso não é execução de APK. |
| [APK debug instalado](debug-apk/device-verification.json) | Aprovado em WebView Android real, com rede desativada: biblioteca e backups, restauração inválida preservando dados, ferramentas, áudio, PNG com exportação nativa, teclado real e rotação. A inspeção usou CDP; esse binário é diferente do APK público. |
| [Pacote de produção](package-verification.json) | Assinatura verificada com `apksigner`; identidade, versão, tamanho, hash e certificado conferem com o manifesto. O APK não é depurável. Essa checagem estática não executa o aplicativo. |
| [APK de produção instalado](signed-apk/device-verification.json) | Aprovado no mesmo APK público assinado, com rede desativada: abertura, presença central, título e conteúdo de nota preservados após reinstalação e capturas físicas em retrato/paisagem. Acessibilidade nativa, sem CDP. |

O teste principal de build/debug passou na
[execução 40894178419, tentativa 2](https://github.com/Lorran1690/elysia-2.0/actions/runs/40894178419/attempts/2).
A [execução complementar 40896390231](https://github.com/Lorran1690/elysia-2.0/actions/runs/40896390231)
também passou, com revisão de testes `826bac8`. As revisões posteriores de QA e
documentação não alteram o código de produção do APK acima.

O APK assinado passou na [execução 40948889883, tentativa 1](https://github.com/Lorran1690/elysia-2.0/actions/runs/40948889883/attempts/1),
com revisão de QA `18f78fc53f31b12dfa60c1307fc36a39d2c6af7f` e requisição de
validação 7. O hash do binário instalado é o mesmo do APK público acima. A origem
do aplicativo continua `d44aab7`; os ajustes posteriores são de QA e documentação.

O [relatório do dispositivo](signed-apk/device-verification.json) comprova abertura,
presença central e reinstalação do mesmo APK com título e conteúdo da nota sintética
preservados, como texto não editável visível dentro da área útil. As árvores de
acessibilidade registram a nota [salva](signed-apk/release-form-saved-record.xml) e
[após reinstalação](signed-apk/release-form-reinstalled-record.xml). O
[relatório do pacote](signed-apk/package-verification.json) confere o binário real;
o [registro do artefato](signed-apk/verification-artifact.json) preserva procedência,
tamanho e hashes conferidos no download.

Capturas físicas de produção: [retrato, 1080×2340](signed-apk/release-portrait.png),
[presença](signed-apk/release-presence.png),
[biblioteca após reinstalação](signed-apk/release-reinstalled-library.png) e
[paisagem, 2340×1080](signed-apk/release-landscape.png).

As capturas já publicadas do APK debug mostram
[retrato](debug-apk/android-portrait.png),
[teclado](debug-apk/android-keyboard.png) e
[presença em paisagem](debug-apk/android-landscape-presence.png).
O teste de produção exige imagem Android `user`, `ro.debuggable=0` e ausência do
socket de depuração do WebView, usando acessibilidade nativa sem CDP.[^chromium]
A validação foi realizada em emulador; não comprova instalação no telefone do
proprietário.

## Limites e preservação

Neural Core Python/PyTorch e ComfyUI não foram portados para Android. O APK não
usa modelos externos, APIs de conversa ou respostas simuladas. A mídia local é
a composição existente; geração neural de imagens/vídeos não foi avaliada no
Android. Voice Core continua pausado.

[preserved-files.json](preserved-files.json) registra sete arquivos idênticos a
`008426a`: três renderizadores, dois PNGs de avatar, o ícone aprovado e o
checkpoint linguístico próprio `sft-model.pt`. O checkpoint permanece preservado
no projeto; isso não significa que ele seja executado no telefone.

Código, APK, manifesto, hashes e evidências públicas ficam no GitHub.
Credenciais, material privado de assinatura, conversas e backups pessoais ficam
fora do repositório público. Os registros usados pelos testes são sintéticos.
Exporte seu backup privado pelo aplicativo antes de atualizar; desinstalar ou
limpar dados remove os registros locais.

[^chromium]: No [código oficial do Chromium 124](https://chromium.googlesource.com/chromium/src/+/124.0.6367.219/android_webview/glue/java/src/com/android/webview/chromium/SharedStatics.java#87), a depuração do WebView não pode ser desativada em builds de depuração. [`BuildInfo`](https://chromium.googlesource.com/chromium/src/+/124.0.6367.219/base/android/java/src/org/chromium/base/BuildInfo.java#373) inclui Android `eng`/`userdebug`, independentemente da flag do aplicativo; por isso a validação de produção usa imagem `user`.

A entrega atual com conexão ao computador está em [phone-connection](../phone-connection/README.md).
