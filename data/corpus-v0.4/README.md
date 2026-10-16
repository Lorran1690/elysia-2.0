# Corpus experimental v0.4

Este diretório guarda o manifesto auditável da coleta autorizada de três obras de Machado de Assis. Os arquivos originais e as versões limpas ficam somente no ambiente local e são ignorados pelo Git; não devem ser publicados automaticamente.

O `audit-manifest.json` registra URLs, hashes, tamanhos, limpeza, divisão e estatísticas. Para reproduzir a limpeza depois de obter os três arquivos aprovados, execute:

```powershell
python -m learning.prepare_corpus_v04
```

O script não baixa arquivos e não inicia treinamento.
