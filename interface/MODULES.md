# Módulos locais

## Knowledge Vault

Crie notas, documentos e fontes com título, conteúdo e URL opcional. A biblioteca
usa SQLite e busca textual FTS5, incluindo busca de palavras sem acento. Importe
TXT ou Markdown em UTF-8 para o formulário, revise e clique em Salvar registro. URLs são
apenas metadados: o aplicativo não baixa páginas nem acompanha links sozinho.

Os limites desta versão são 500 registros e 20.000 caracteres por conteúdo.
Arquivos TXT/MD de importação têm limite de 80 KB. A busca considera título e
conteúdo; não usa embeddings nem um modelo externo. A edição é explícita e a
exclusão pede confirmação. Não há lixeira: exporte antes de excluir se precisar
recuperar registros depois.

O banco é privado e fica em `%LOCALAPPDATA%\Elysia\vault.sqlite3` no Windows ou
`~/.local/share/Elysia/vault.sqlite3` em outros sistemas. `ELYSIA_DATA_DIR` pode
selecionar outro diretório. O armazenamento não é criptografado: a proteção é a da
conta do sistema. Documentos, notas, fontes e backups pessoais nunca são versionados
no Git nem usados automaticamente para treinar o núcleo.

Use **Exportar biblioteca** para baixar JSON com SHA-256 do conteúdo. Guarde em
armazenamento privado fora do computador. **Restaurar biblioteca** valida o hash,
os limites e todos os registros antes de concluir. Importações são transacionais,
idempotentes para registros idênticos e preservam registros existentes. Um conflito
de identificador com conteúdo diferente cancela a importação inteira. O hash
permite verificar integridade, mas não autentica a autoria do arquivo.

A biblioteca não é enviada ao chat: os resultados são apresentados diretamente
para consulta do usuário. Isso não representa memória semântica ou conhecimento
aprendido pelo modelo. Conversas e biblioteca têm backups separados.

## Código e ferramentas

Quatro ferramentas determinísticas, executadas somente pelo botão do usuário:
calculadora aritmética limitada, validação de JSON, estatísticas de texto e SHA-256
do texto UTF-8. A calculadora aceita apenas operações numéricas permitidas por um
leitor de AST, com limites de tamanho e expoente. Não executa Python, imports,
comandos, arquivos ou expressões arbitrárias. O JSON é validado sem reformatar o
original; chaves duplicadas e constantes não JSON são rejeitadas.

As ferramentas não são chamadas autonomamente pelo Transformer. Terminal,
automações e controle do computador continuam indisponíveis.

## Media Studio

Visualização temporária no navegador de PNG/JPEG/WebP/GIF, MP3/WAV/OGG/M4A e
MP4/WebM, até 100 MB. A compatibilidade de codecs depende do navegador. O arquivo
não é enviado ao servidor, salvo na biblioteca, usado no treino ou publicado.
Fechar o painel/arquivo libera a referência temporária; o arquivo original permanece
no local escolhido pelo usuário. O módulo não gera, edita ou reconhece mídia.
O microfone não é ativado. Voice Core continua pausado.
