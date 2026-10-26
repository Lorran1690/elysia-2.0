# Interface v11 e módulos integrados

A interface enviada pelo proprietário em `elysia-v11-corpo-preservado.zip` foi
integrada ao aplicativo existente. O protótipo de conversa demonstrativa não
substitui o chat real: o aplicativo continua usando o Transformer próprio local,
ainda experimental, com os mesmos limites de qualidade e contexto.

## Avatar

Os arquivos `avatar-body.png` e `avatar-bust-violet.png` foram copiados sem
alteração de bytes. O rig procedural e o desenho por partículas são da interface
fornecida. Não são um novo modelo 3D ou geração de vídeo neural.

Aparência permite selecionar busto ou cintura para cima, manter o holograma em
pré-visualização, acenar, ajustar o enquadramento e controlar a quantidade de
partículas. A cabeça acompanha o cursor. Preferências antigas recebem os novos
campos sem apagar paleta e tamanho. A saudação visual não altera o estado real do
Neural Core e termina mesmo com movimento reduzido ou falha de imagem.

## Funcionalidades preservadas

- Conversa local, nova conversa, exportação e restauração de backup privado.
- Knowledge Vault: notas, documentos, busca e backup privado.
- Editor de código, validação e ferramentas locais.
- Bancada de análise estática e catálogo de habilidades com limites explícitos.
- Media Studio: imagens, áudio sintetizado e animações; cinema 3D contínuo com trilha.
- Imagens por difusão e integração experimental de vídeo por ComfyUI local.
- Exportação para pasta escolhida, incluindo uma pasta sincronizada do Drive quando
  instalada e configurada pelo usuário. A atualização não configura a conta Drive.

O Voice Core permanece pausado. O pacote Windows não inclui ComfyUI nem seus pesos.
Não há avanço de qualidade linguística ou validação nova de vídeo neural neste trabalho.

## Preservação e verificação

Somente arquivos de implementação e os dois avatares necessários foram incorporados;
referências, prompts privados e capturas do ZIP não são publicados. O manifesto em
`reports/interface-v11/source-manifest.json` registra os hashes dos arquivos usados.

`test-avatar-browser.py` verifica a migração de preferências, decodificação das
referências, seleção corpo/busto, controles, navegação dos módulos e chat conectado.
No modo fonte usa núcleo simulado; no Windows é executado contra o EXE real.
Os demais testes de módulos, mídia, bancada e geração continuam na compilação Windows.
