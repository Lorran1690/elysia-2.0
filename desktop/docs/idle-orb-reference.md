# Orb Core 3D - analise e preview idle

## Referencia analisada

Fonte local recebida para a tarefa: `WhatsApp Video 2026-10-16 at 19.32.22.mp4`.

- Duracao: 20,26 s.
- Video: 480 x 864, 30 fps.
- Amostragem visual: aproximadamente 1 s, 5 s, 9 s, 13 s e 17 s.
- O arquivo de referencia e seus quadros nao foram copiados para o repositorio.

## Caracteristicas observadas

- Fundo azul-ardosia muito escuro, sem elementos decorativos concorrendo com o nucleo.
- Particulas em ouro, laranja e pontos amarelo-quentes mais intensos.
- O conjunto alterna entre nuvem difusa, malha irregular e uma compressao em anel/ovalo.
- A forma nao permanece esferica: a silhueta abre, se dobra, cria vazios e volta a condensar.
- Alguns polos tornam-se mais brilhantes e conectam grupos temporariamente.
- As linhas nascem e desaparecem dentro do volume; elas nao formam uma grade estatica.
- O chat aparece baixo e deslocado para a esquerda/centro na referencia, deixando o orbe como foco principal.

## Implementacao deste preview

O orbe e uma geometria Three.js real, composta por pontos em volume e `LineSegments`. Cada frame atualiza somente buffers prealocados. A procura de vizinhos usa uma grade espacial hash; conexoes sao recalculadas em intervalos dependentes do preset, nao a cada particula React.

O estado `idle` combina respiracao, fluxo interno, uma cavidade ambulante, mudanca de densidade e uma compressao ocasional. As transicoes sao temporais e nao reinicializam a cena.

| Perfil | Particulas | Limite de conexoes | Atualizacao de conexoes |
| --- | ---: | ---: | ---: |
| Baixa | 1.200 | 320 | 104 ms |
| Media | 2.400 | 600 | 82 ms |
| Alta | 3.600 | 900 | 66 ms |

O painel do preview mede FPS, particulas e conexoes. Browsers nao oferecem medicao confiavel de CPU, VRAM ou uso de GPU para esta cena; esses valores devem ser conferidos pelas ferramentas do Windows durante a validacao na GTX 1650, sem treinamento CUDA em paralelo.

## Diferencas conhecidas

- A referencia e uma filmagem vertical de um monitor, portanto nao fornece um plano de camera ou parametros 3D reproduziveis com precisao absoluta.
- Este preview recria os comportamentos visuais observados, mas nao declara fidelidade exata ao video.
- O painel de chat foi omitido intencionalmente: o ponto de parada desta fase autoriza apenas a estrutura desktop e o orbe `idle`.
- Os estados `listening`, `thinking`, `speaking` e `sleeping`, a reacao ao mouse e o adaptador neural nao foram iniciados.

## Revisao visual solicitada

Validar em tela real a densidade, a velocidade do fluxo, o contraste dourado e o tamanho relativo do orbe. Apos essa revisao, os ajustes visuais devem anteceder a criacao de outros estados ou da interface de chat.
