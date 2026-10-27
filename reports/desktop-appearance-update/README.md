# Controles de presença e atualização interna · 2.2

Os controles originais voltaram a Configurações → Aparência, com formas fixas
orbe/avatar e automática, prévia e visualização central. As escolhas são gravadas
com as preferências privadas. Os arquivos de renderização e pesos listados em
`preserved-files.json` permanecem idênticos aos da entrega anterior.

`source-ui-verification.json` e as capturas `source-*` registram a prévia no
Chromium Linux com uma resposta sintética para testar somente a interface.
Não representam a execução do instalador nem avaliação do Neural Core.

O workflow Windows verifica o instalador, a janela WebView2, persistência SQLite,
a consulta real do atualizador e a recusa de instalar sem download verificado.
`check-source-migration.py` reproduz a migração antiga e a janela compacta.
`check-updater-ui.py` reproduz uma fixture de IPC no navegador Chromium, que
testa os estados visuais de uma publicação futura;
ela não baixa nem executa instalador e não está no transporte de produção.
O download e a instalação de uma atualização futura completa ainda não foram
exercitados. Veja `desktop/UPDATES.md` para o procedimento e a confiança por
HTTPS, metadados do GitHub e hashes.

A primeira execução Windows (`40530826106`, fonte `0c9bd67`) compilou e testou
Rust, validou os controles nativos e consultou o GitHub, mas o teste tentou
substituir a ponte imutável do Tauri para simular a versão futura. A execução
parou nesse teste e não publicou um instalador. A fixture foi transferida para
o teste Chromium separado; a janela nativa usa somente comandos reais.

## Entrega Windows verificada

Fonte `9781d75fd4abd9c99d2c9dde29f173822e995a33`, Elysia 2.2.0.
[Instalador publicado](https://github.com/Lorran1690/elysia-2.0/releases/download/native-9781d75fd4ab/Elysia-Setup-x64.exe).
O workflow nativo `40533155914` e os testes Windows/Linux `40533156025` passaram.
Seis testes Rust passaram. Os arquivos `windows-*` foram baixados da publicação
e conferidos com os hashes de cada asset no GitHub. As capturas mostram a janela
WebView2 real; a tela de atualização consulta o GitHub real e não simula versão
futura. O instalador foi executado, reinstalado e removido preservando os dados
privados de teste. Isso não instala o aplicativo no computador do proprietário.

O instalador baixado tem 151.563.728 bytes e SHA-256
`4b715f21d0c9bc7304edaa0dbf2fa44da7aae9b0ad343ea719b3a51c037703a0`.
`release-verification.json` registra URLs, hashes, tamanho, origem e limites dos
testes. O manifesto `elysia-update.json` coincide com a identidade do instalador
publicado. A atualização completa entre duas versões futuras não foi executada.
