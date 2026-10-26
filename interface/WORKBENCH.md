# Bancada de análise e catálogo de habilidades

No aplicativo, abra **Bancada de análise** na barra lateral.

- **Código Python:** extraia classes, funções, importações e nomes de chamadas,
  com linhas e um grafo clicável. A seleção localiza o trecho no editor.
- **Arquivo:** escolha um arquivo de até 4 MB para primeira inspeção de PE/EXE/DLL,
  ELF e ZIP/APK. Outros formatos recebem tamanho, hash, entropia e strings.
  PE inclui seções e nomes de bibliotecas importadas quando resolvíveis.
- **Revisão:** compare o texto atual com uma proposta, aceite somente no editor
  e desfaça as últimas cinco aceitações da sessão. Arquivos em disco não mudam.
- **Anotações:** salve notas no Vault privado. Exporte/restaure um projeto JSON
  com código atual, proposta, anotações e relatório de arquivo.

A análise não executa o arquivo, não importa módulos enviados, não extrai ZIPs,
não faz chamadas externas e não usa um LLM. O arquivo selecionado é enviado
somente ao servidor local do aplicativo, processado em memória e descartado.
Projetos e notas podem conter dados privados: exporte para armazenamento privado,
nunca para o repositório público. O projeto não é salvo automaticamente; fechar
ou trocar de painel descarta o estado que não foi exportado. O registro de
atividade e o histórico de desfazer são temporários e não fazem parte do backup.
Relatórios importados de projetos não são verificados novamente até nova análise.

A inspeção é inicial: não descompila código, não verifica segurança, não identifica
malware e não comprova o comportamento do programa. Entropia é só uma estatística.
O grafo vem da sintaxe de um arquivo, com limites de tamanho; não resolve chamadas
reais, dependências entre arquivos, imports dinâmicos ou relações inferidas.
A aceitação de texto não equivale a teste ou execução do código proposto.

## Referência Eleven

Analisado: [Zfinix/eleven, e3950adab738](https://github.com/Zfinix/eleven/tree/e3950adab7381a8f4a8dc11ff8a9b20b47e48c73),
versão 0.1.13. README, LICENSE e app/package.json consultados. Licença declarada
Apache-2.0. Eleven é um app React/TypeScript sobre GPUIX/Bun, com agentes ACP e
ferramentas MCP, Ghidra/REA ou Rizin, jadx e depuração LLDB conforme o recurso.

A Elysia aproveita **o fluxo de primeira inspeção, revisão explícita e projetos
exportáveis como referência arquitetural**, com implementação Python/React própria.
Não redistribui o código, logotipos ou os motores do Eleven. Ghidra, Rizin, ACP,
MCP, decompilação, patch binário e depurador não estão integrados. Não foram
executados instaladores remotos nem conectados agentes externos ao Neural Core.
Isso é a primeira entrega desse fluxo, não equivalência funcional ao Eleven.

## Habilidades e evolução

O novo painel mostra 21 áreas do memorando com busca, filtro de estado e
exportação de catálogo. Cada item informa descrição, requisitos, origem,
permissões, disponibilidade offline e limites. Neural Core continua experimental;
Voice Core pausado. As integrações dos outros repositórios do memorando ainda
precisam de avaliação específica. Adicionar uma referência não instala a ferramenta.

O memorando original está preservado em docs/MEMORANDO-FUNCIONAL-2026-10-26.md,
com um aviso de planejamento. Alegações do documento não substituem as evidências
do aplicativo; Stable Diffusion não está presente neste checkout. A interface e
os testes distinguem planejamento, implementação parcial e recurso disponível.

## Verificação

Testes de PE/ELF e ZIP sintéticos, limites, arquivos truncados, ausência de execução,
origem das relações Python e diffs; APIs restritas ao servidor local; navegador
verifica seleção do código, aceitar/desfazer, inspeção sem alterar o arquivo,
backup de projeto, rejeição de estrutura inválida, nota no Vault e catálogo.
A publicação Windows exige esses fluxos no EXE real antes de liberar o pacote.
Os testes não equivalem a auditoria de segurança ou avaliação independente.
