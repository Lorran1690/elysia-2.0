# Interface com Neural Core

A interface enviada pelo proprietário foi integrada ao Transformer próprio, usando
por padrão `artifacts/aira-dialogue-v1/run-001/sft-model.pt` e seu BPE 2048 validado.
Não usa APIs de linguagem nem pesos externos. Este modelo ainda falha em conversas
gerais; integrar a interface não representa melhoria de inteligência.

No PowerShell, na pasta do repositório, com o ambiente Python já instalado:

```powershell
.\.venv\Scripts\python.exe -m interface.server
```

Abra **http://127.0.0.1:8765** no navegador. Não abra o HTML diretamente.
Encerre com Ctrl+C. A inferência usa CPU, portanto esta interface pode ser testada
mesmo enquanto o driver CUDA estiver sendo diagnosticado. Não executa treinamento.

O chat envia o histórico ao processo local. A conversa atual é salva no navegador
após cada resposta. Use **Exportar backup** para guardá-la fora do computador e
**Restaurar backup** para recuperá-la. Nova conversa limpa o histórico atual.
O contexto do piloto é curto e falhas de geração não são simuladas.

Para abrir como aplicativo Windows, consulte [DESKTOP.md](DESKTOP.md).

O orbe/avatar acompanha o processamento e a apresentação do texto. Não há áudio,
captura de microfone ou geração de mídia. A biblioteca privada, ferramentas
locais e visualização de mídia estão descritas em [MODULES.md](MODULES.md). Ajustes visuais continuam disponíveis.

React 18.3.1, ReactDOM 18.3.1 e Babel 7.29.0 estão incluídos localmente em
`web/vendor`, com suas licenças MIT e integridade SHA-384 verificada contra o HTML
original. Fontes remotas foram removidas; a interface usa as fontes alternativas
do sistema. O carregamento e as conversas funcionam sem serviços externos.
O servidor escuta exclusivamente em 127.0.0.1, valida Host/Origin, limita tamanho
e formato das mensagens e serve somente os arquivos da interface.

Arquivos visuais importados do ZIP `elysia-avatar-cabeca-integrada (1).zip` fornecido
pelo proprietário. Material de referência, prompts e screenshots do ZIP não foram
adicionados ao repositório. A imagem do avatar é usada pela interface.
