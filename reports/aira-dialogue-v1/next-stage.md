# Condições para avançar para conversas complexas

O objetivo geral continua sendo um Neural Core próprio capaz de conversas
complexas. Este piloto mede interações curtas e não demonstra essa capacidade,
mesmo que a loss melhore ou alguns casos sejam acertados.

## Limites concretos do ambiente

O executor observado tem 3 CPUs lógicas, aproximadamente 9,7 GiB de RAM e nenhuma
GPU CUDA. Não há credenciais nem serviço de computação externa configurados no
ambiente; as ferramentas disponíveis não provisionam GPU. O modelo atual tem
2.567.616 parâmetros, contexto máximo 512 e pré-treino em uma base de cerca de
2,3 milhões de tokens de corpus antes de reamostragem. O piloto novo só usa janelas
inteiras de até 256 tokens. Essas escalas não sustentam uma promessa de capacidade
geral comparável ao ChatGPT. Treinar repetidamente a mesma amostra não supre
conhecimento, diversidade nem contexto.

## Próximo experimento justificável

1. Ampliar o pré-treino com português variado e procedência verificável. Manter
   atribuição, licença, versão imutável, deduplicação por documento e teste separado.
   Os novos diálogos sintéticos não substituem essa base linguística ampla.
2. Adicionar instruções e conversas revisadas por pessoas, com identificação clara
   de autoria e verificação factual. Medir qualidade por domínio e reduzir a
   dependência de uma única família de respostas sintéticas.
3. Disponibilizar computação adequada para experimentar modelos próprios maiores
   e contextos longos. Definir um orçamento de tokens e medir vazão no ambiente
   real antes de iniciar o treinamento maior. Uma GPU, por si só, não garante
   competência: os ganhos precisam ser medidos em dados separados.
4. Congelar novo protocolo e novo teste independente. Os benchmarks já consumidos
   permanecem diagnósticos históricos. Avaliar conversas reais com vários turnos,
   correções, referências a turnos distantes, explicações, código e incerteza.
   Fazer revisão humana independente além da avaliação automatizada.

A meta ampla depende dessa expansão de dados, validação e computação. Não há
base técnica para declarar sucesso a partir de um piloto pequeno ou para
prometer que basta aumentar o número de passos do modelo atual.
