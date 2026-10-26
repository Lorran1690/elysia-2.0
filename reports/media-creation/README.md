# Ferramentas de criação e código

O pacote Windows foi aprovado com o executável real e dois testes de navegador:
os módulos existentes e os novos fluxos de criação. Foram aprovados 188 testes
Python e 3 testes do motor JavaScript, em Windows e Linux. O relatório nativo
`windows-media.json` confirma a exportação de PNG 640×360, WAV PCM mono de
22.050 Hz, decodificação de WebM, cancelamento, restauração de projeto e exportação
e validação de código. A prévia HTML não executou scripts nem navegou para a URL
do teste; nenhuma requisição externa foi observada nesses testes.

Os três exemplos gerados no teste de origem foram enviados à pasta privada do
proprietário no Google Drive pelo conector do chat e verificados por leitura de
metadados: imagem/png, audio/wav e video/webm, sem compartilhamento público. Os
identificadores pessoais da pasta e dos arquivos não são registrados no Git.
O endereço da pasta é fornecido diretamente ao proprietário no chat.

Esse envio via conector **não é uma integração de upload direto do EXE**. O app
oferece gravação em pasta escolhida, lembrada pelo navegador, com permissão e opção
para as próximas exportações da sessão. A sincronização depende do Google Drive
para computador e ainda precisa ser configurada no PC do proprietário. O teste
desse caminho usa um diretório simulado, incluindo colisão e permissão negada;
não é verificação de sincronização real na máquina do proprietário.

A criação é composição gráfica, síntese de tons/melodias e animação curta sem
áudio. Não há modelos de IA generativa de mídia, voz ou programação integrados.
Os modelos iniciais de código são determinísticos, a validação não executa o
programa e o rascunho fica no navegador. O núcleo linguístico próprio e o Voice
Core mantêm o estado anterior.

Veja `verification.json` para hashes, fontes de verificação e link do pacote e
[MEDIA.md](../../interface/MEDIA.md) para limites e instruções.
