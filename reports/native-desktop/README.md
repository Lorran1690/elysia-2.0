# Interface desktop Tauri

A interface React/TypeScript foi compilada com Vite e organizada em quatro áreas:
Conversas, Biblioteca, Criação e Desenvolvimento. Configurações incluem aparência,
comportamento das conversas, acessibilidade, dados privados, diagnóstico e música.

O ícone foi mostrado como proposta e aprovado pelo proprietário antes de ser usado.
Três faixas instrumentais originais acompanham o app, com licença CC0 e composição
reproduzível. Three.js/React Three Fiber exibem o espectro do áudio; GSAP anima
apenas transições de painéis. Avatar, orbe, rig e imagens originais não foram
alterados, conforme hashes em desktop/branding/preservation.json.

`source-ui-verification.json` usa a fixture linguística sintética, sem carregar ou
avaliar o Neural Core. Confere áudio real, volume, faixa/pausa, temas, histórico,
proteção contra sobrescrita de histórico ilegível, Vault, ferramentas, composição
PNG e busca. As capturas source são dessa verificação.

A publicação Windows exige teste do instalador e da janela WebView2 Tauri real.
Depuração CDP é ativada somente por modo E2E explícito com diretório privado e perfil
isolado; a configuração padrão não abre porta de depuração. Esse modo passa os
argumentos por API porque o WebView2 Runtime 150 ignora as variáveis de depuração
em processos elevados de runners. Não é necessário abrir navegador externo.

O núcleo, treinamento e modelos de geração não foram ampliados. A biblioteca e os
backups de conversas permanecem privados. A migração do navegador antigo é manual,
por exportação/importação de JSON. O objetivo de vídeos neurais realistas não faz
parte desta atualização de interface e continua sem validação.

O instalador nativo verifica o WebView2 e contém o bootstrapper oficial Microsoft,
autenticado no build, para preparar o Runtime somente se ausente. A instalação
desse pré-requisito pode precisar de internet; não é um motor de geração remoto.
O fluxo de instalação em máquina sem Runtime é documentado e compilado; a execução
no runner usa o Runtime já instalado.

## Pacote Windows verificado

[Instalador nativo](https://github.com/Lorran1690/elysia-2.0/releases/tag/native-aebf8e6c70eb), fonte `aebf8e6c70ebaf998a801362fcc3113c18ce68e3`.
`windows-ui-verification.json` e `windows-installer-verification.json` vieram da
Release e foram conferidos contra os digests publicados. As capturas Windows são
da janela nativa real, com perfil e dados sintéticos isolados. O relatório confirma
reprodução de áudio, volume, troca de faixa, temas, fontes, histórico SQLite,
proteção contra sobrescrita em falha de restauração, biblioteca, código, composição,
cinema e busca. Não mede inteligência nem vídeo neural. Incluídos 550 arquivos de
licença/atribuição de dependências Rust e os avisos npm/Python.

`release-verification.json` registra URLs, tamanhos e SHA-256 observados dos assets.
O aplicativo não foi instalado no computador do proprietário por esta sessão.
