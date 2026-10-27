# Atualizações pelo aplicativo

Em **Configurações → Sistema**, clique em **Verificar atualizações**. O aplicativo
consulta as publicações nativas do repositório `Lorran1690/elysia-2.0`. Quando houver
uma versão mais nova, **Baixar atualização** recebe o instalador e verifica seu
tamanho e SHA-256. O download não instala nem fecha a janela.

Salve os arquivos abertos nos editores. Depois, **Fechar Elysia e instalar** abre o
instalador e encerra a Elysia. Termine as etapas do instalador e marque a opção de
abrir o aplicativo. O destino é a mesma pasta da instalação atual, no usuário
atual. Conversas, preferências, Biblioteca e mídia continuam fora dessa pasta.

A edição portátil permite verificar versões, mas não é convertida automaticamente
em uma instalação. As versões anteriores à 2.2 ainda precisam receber esta primeira
atualização pelo instalador; o botão passa a servir para as versões seguintes.

## Identidade e verificação

- Não há consulta, download ou instalação automática ao abrir a Elysia.
- O frontend não pode fornecer URLs ou caminhos de executáveis ao atualizador.
- As consultas usam o endereço fixo da API GitHub, HTTPS e limites de tamanho.
  Redirecionamentos dos downloads ficam limitados aos servidores de publicação
  do GitHub, sem permitir HTTP ou portas alternativas.
- Cada build Windows publica `elysia-update.json`, com versão, número crescente
  da compilação, commit completo, tag e identidade exata do instalador.
- Só são aceitas publicações `native-<12 primeiros caracteres do commit>`, com o
  manifesto no próprio repositório e o instalador `Elysia-Setup-x64.exe`.
- Tamanho e SHA-256 do manifesto precisam coincidir com os metadados do arquivo
  na API GitHub. O download é gravado em arquivo temporário e só se torna um
  instalador pronto depois da verificação completa. A integridade é verificada
  novamente imediatamente antes de executar.
- Uma compilação só é oferecida se seu número for maior que o atual e sua versão
  não representar um downgrade. A numeração vem de `GITHUB_RUN_NUMBER` deste
  workflow nativo, independente de mudanças visuais sem alteração do semver.
- Este é um atualizador do instalador Inno existente, baseado em HTTPS e hashes
  dos arquivos publicados no GitHub. Não usa o plugin de atualização Tauri nem
  uma assinatura independente do projeto. O instalador continua sem assinatura
  Authenticode do projeto; a conta e o repositório GitHub são a origem de confiança.
- Falhas de conexão, tamanho ou integridade não executam um instalador nem
  substituem a instalação atual. Conversas e dados privados não são enviados.

O workflow publica o manifesto somente após os testes do pacote instalado, junto
ao instalador e seus relatórios. Testes Rust verificam URLs, identidade, hashes,
truncamento, corrupção, repetição e downgrade. A reinstalação real do pacote no
Windows verifica a preservação dos dados privados. O teste da interface consulta
o atualizador e sua interface reais no Windows. Separadamente, uma fixture de IPC
no Chromium Linux exercita os estados visuais de disponibilidade, progresso,
download e instalação, sem baixar ou executar arquivos. Essa fixture não existe
no transporte de produção e não substitui a ponte imutável do Tauri. A atualização futura completa de
uma versão para outra permanece distinta dessas verificações.

Referências utilizadas: [Tauri 2.12.5 AppHandle](https://docs.rs/tauri/2.12.5/tauri/struct.AppHandle.html),
[reqwest 0.12.28 Redirect Policy](https://docs.rs/reqwest/0.12.28/reqwest/redirect/struct.Policy.html),
[GitHub release assets e digest](https://docs.github.com/en/rest/releases/assets).
