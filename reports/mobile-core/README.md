# Portabilidade do Neural Core

Primeira etapa da execução local no Android: exportação dos pesos próprios para
float32 little-endian, com nomes, dimensões, offsets e SHA-256 no manifesto.
Reprodução: `python scripts/export-mobile-core.py --output artifacts/mobile-core`.
Requer o ambiente de treinamento com PyTorch e NumPy.

O checkpoint original permanece intacto. Foram exportados 44 tensores,
10.270.464 bytes, reconstruídos e comparados exatamente com todos os valores
originais em float32. O loader também confere a identidade do tokenizador BPE.
O tokenizador correspondente acompanha o pacote em `tokenizer.json`.

Este formato ainda precisa de um executor de operações Transformer e BPE no
Android. Não foi integrado ao APK de distribuição, não comprova inferência no
telefone e não melhora os resultados de conversação do checkpoint, cuja avaliação
anterior permanece reprovada. O APK público continua sendo o build 7 verificado.

A geração neural de imagens e vídeo também permanece pendente: o pipeline ComfyUI
do computador não é executável diretamente no Android. Não foi substituído por
serviços externos, respostas simuladas ou apresentações de slides. Voice Core
permanece pausado.
