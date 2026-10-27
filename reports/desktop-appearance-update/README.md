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
