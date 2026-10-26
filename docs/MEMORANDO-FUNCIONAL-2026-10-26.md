> Documento de referência fornecido pelo proprietário. É planejamento de longo prazo,
> não uma lista de funcionalidades já entregues. O catálogo no aplicativo e as notas
> da versão indicam o estado verificado. A integração Stable Diffusion citada no
> documento não existia no checkout recebido; agora há um adaptador ComfyUI com
> teste real de imagem em CPU. Veja interface/GENERATIVE-MEDIA.md para os limites.

# MEMORANDO TÉCNICO E FUNCIONAL
## E.L.Y.S.I.A. 2.0 — Catálogo Geral de Habilidades e Capacidades

**Data:** 26 de outubro de 2026  
**Projeto:** E.L.Y.S.I.A. 2.0  
**Assunto:** Definição das capacidades, ferramentas, módulos e objetivos de desenvolvimento da assistente inteligente E.L.Y.S.I.A.  
**Natureza:** Documento de referência e planejamento de longo prazo.

---

## 1. OBJETIVO

A E.L.Y.S.I.A. deverá evoluir para uma assistente inteligente pessoal, multimodal, modular e progressivamente autônoma, com identidade, memória e inteligência próprias.

Sua finalidade não será apenas conversar com o usuário, mas também **pesquisar, aprender por treinamento, recuperar conhecimentos, programar, criar conteúdos digitais, operar ferramentas, organizar atividades e executar tarefas autorizadas**.

O sistema deverá possuir capacidades de:

- Conversação e raciocínio.
- Memória persistente e recuperação de conhecimentos.
- Programação de sites, aplicativos e ferramentas.
- Produção de vídeos e animações.
- Geração e edição de imagens.
- Produção e processamento de áudio.
- Síntese e reconhecimento de voz.
- Controle supervisionado do computador.
- Pesquisa na internet.
- Produção de documentos e planilhas.
- Análise de dados e finanças.
- Segurança digital.
- Coordenação de agentes especializados.
- Administração de projetos e tarefas.
- Criação de conteúdos para redes sociais.
- Interação por avatar tridimensional.

**Princípio essencial:** as ferramentas externas ampliam suas habilidades, mas não substituem automaticamente seu cérebro, identidade, personalidade ou memória.

---

## 2. INTELIGÊNCIA PRÓPRIA — NEURAL CORE

A E.L.Y.S.I.A. deverá possuir uma rede neural linguística própria, desenvolvida e treinada progressivamente.

### Capacidades desejadas

1. Compreender linguagem natural em português brasileiro.
2. Manter conversas coerentes e contextualizadas.
3. Responder perguntas e fornecer explicações.
4. Interpretar instruções e objetivos.
5. Formular planos de execução.
6. Aprender padrões a partir de treinamento supervisionado e experimentos controlados.
7. Utilizar conhecimentos recuperados de sua biblioteca.
8. Reconhecer incertezas e solicitar informações quando necessário.
9. Identificar erros e utilizar avaliações para orientar melhorias.
10. Desenvolver progressivamente competência em programação, planejamento e interação.

### Requisitos técnicos

- Transformer e tokenizador próprios.
- Treinamento e avaliação reproduzíveis.
- Checkpoints versionados.
- Dados com origem e direitos registrados.
- Separação entre treino, validação e teste.
- Métricas objetivas de competência.
- Compatibilidade com o hardware disponível.
- Nenhuma substituição silenciosa do modelo por um LLM externo.

**Distinção obrigatória:** uma ferramenta conseguir realizar determinada atividade não significa que o Neural Core tenha aprendido essa habilidade em seus pesos.

A inteligência conversacional continua sendo uma prioridade de desenvolvimento, independentemente da quantidade de ferramentas integradas.

---

## 3. MEMÓRIA E CONHECIMENTO — KNOWLEDGE VAULT

A E.L.Y.S.I.A. deverá possuir uma biblioteca digital híbrida, capaz de crescer progressivamente e armazenar conhecimentos em diferentes formatos.

### Capacidades

- Importar livros, apostilas, artigos, documentos e códigos.
- Guardar imagens, áudios, vídeos e projetos.
- Indexar documentos.
- Pesquisar por palavras e expressões.
- Recuperar trechos com indicação das fontes.
- Identificar documentos duplicados.
- Organizar conteúdos por temas, categorias e projetos.
- Registrar memórias de conversas autorizadas.
- Associar conhecimentos a objetivos e tarefas.
- Preservar histórico e versões.
- Exportar conjuntos de dados aprovados para treinamento neural.
- Gerar backups criptografados.
- Restaurar a biblioteca.
- Sincronizar arquivos selecionados com armazenamento remoto.

### Arquitetura

**Local:** armazenamento principal no computador.  
**Nuvem:** Google Drive como extensão e backup.  
**Banco:** SQLite/FTS5 inicialmente, com possibilidade de evolução.

A biblioteca deve continuar funcionando offline para os arquivos locais.

Documentos adicionados ao Vault não devem ser automaticamente utilizados para treinamento.

---

## 4. GRAFOS DE CONHECIMENTO — KNOWLEDGE GRAPH

**Referência:** https://github.com/Graphify-Labs/graphify

Além de guardar informações, a E.L.Y.S.I.A. deverá compreender e consultar relações estruturadas entre elas.

### Habilidades

- Criar mapas de dependências de software.
- Identificar relações entre funções, classes e módulos.
- Relacionar documentos, conceitos e projetos.
- Localizar componentes afetados por mudanças.
- Pesquisar caminhos entre informações.
- Visualizar grafos interativos.
- Distinguir relações extraídas de relações inferidas.
- Registrar a origem de cada conexão.
- Fornecer conhecimento estrutural ao Code Core e ao Cognitive Core.

### Exemplo

"Elysia, identifique todos os módulos que dependem do sistema de autenticação."

A resposta deverá utilizar relações efetivamente extraídas do projeto e indicar os arquivos correspondentes.

**Estratégia:** começar pela análise local de código, sem depender de modelos externos de linguagem.

---

## 5. PROGRAMAÇÃO E DESENVOLVIMENTO — CODE CORE

**Referências:**

- https://github.com/worldflowai/everything-claude-code
- https://github.com/garrytan/gstack

A E.L.Y.S.I.A. deverá possuir um ambiente de desenvolvimento supervisionado.

### Capacidades de programação

- Ler e compreender a estrutura de projetos.
- Pesquisar códigos e documentações.
- Criar arquivos e módulos.
- Desenvolver sites e aplicações.
- Construir APIs e integrações.
- Trabalhar com bancos de dados.
- Preparar correções de bugs.
- Refatorar código.
- Identificar duplicações.
- Propor melhorias arquiteturais.
- Criar testes unitários e de integração.
- Executar validações autorizadas.
- Comparar alterações por diff.
- Detectar possíveis vulnerabilidades.
- Gerenciar branches e commits locais.
- Reverter alterações.
- Produzir documentação técnica.
- Gerar relatórios de auditoria.

### Papéis especializados

O Code Core deverá organizar processos de trabalho equivalentes aos de:

- Arquiteto de software.
- Planejador técnico.
- Programador.
- Revisor de código.
- Especialista em segurança.
- Analista de testes.
- Especialista em depuração.
- Revisor de interface.
- Responsável pela documentação.

Esses papéis representam fluxos e responsabilidades, não obrigatoriamente modelos neurais independentes.

### Processo de desenvolvimento

**Solicitação → Análise → Planejamento → Proposta → Revisão → Aprovação → Aplicação → Testes → Entrega.**

A edição de arquivos deverá respeitar os limites dos diretórios autorizados e oferecer mecanismos de reversão.

### Linguagens e tecnologias de interesse

Python, JavaScript, TypeScript, HTML, CSS, SQL, Rust, React, Node.js e outras linguagens necessárias aos projetos.

---

## 6. ORQUESTRAÇÃO DE AGENTES — COGNITIVE CORE

**Referência:** https://github.com/bytedance/deer-flow

A E.L.Y.S.I.A. deverá administrar tarefas complexas dividindo-as em operações menores.

### Habilidades

- Interpretar objetivos.
- Criar planos.
- Dividir tarefas.
- Estabelecer prioridades.
- Coordenar agentes ou ferramentas especializadas.
- Controlar dependências.
- Executar etapas independentes.
- Salvar o estado da atividade.
- Retomar tarefas interrompidas.
- Gerenciar cancelamentos.
- Identificar falhas.
- Realizar novas tentativas quando apropriado.
- Reunir resultados.
- Produzir relatórios de conclusão.
- Administrar limites de CPU, GPU, RAM e disco.

### Exemplo

"Elysia, crie uma apresentação sobre inteligência artificial."

O Cognitive Core deverá coordenar pesquisa, recuperação de fontes, criação do documento, preparação de elementos visuais e exportação.

A autonomia será ampliada conforme as avaliações demonstrem capacidade e segurança, sem liberar ações irrestritas.

---

## 7. CONTROLE DO COMPUTADOR — COMPUTER CONTROL CORE

**Referência:** https://github.com/trycua/cua

A E.L.Y.S.I.A. deverá possuir ferramentas para operar o computador e interagir com aplicativos.

### Habilidades

- Identificar janelas abertas.
- Localizar aplicativos.
- Inspecionar elementos de interface.
- Acionar botões e menus.
- Movimentar e clicar com o mouse.
- Utilizar o teclado.
- Inserir textos.
- Navegar em aplicativos.
- Trabalhar com navegadores.
- Abrir arquivos.
- Executar fluxos supervisionados.
- Verificar resultados de ações.
- Cancelar atividades.
- Registrar operações.
- Trabalhar em ambientes isolados quando apropriado.

### Integração

O Cua Driver deverá ser conectado ao Cognitive Core, ao Vision Core e ao sistema de permissões.

### Proteções

- Controle de quais aplicativos podem ser utilizados.
- Consentimento específico para captura de tela.
- Indicador visível de sessão de captura.
- Revogação de acesso.
- Confirmação de ações sensíveis.
- Proteção contra comandos destrutivos.
- Logs e limites de execução.

A autorização geral de desenvolvimento não substitui a autorização necessária para ações particulares sobre contas, dados privados ou aplicativos sensíveis.

---

## 8. VISÃO COMPUTACIONAL — VISION CORE

A E.L.Y.S.I.A. deverá interpretar informações visuais provenientes de imagens e de sessões de tela autorizadas.

### Capacidades desejadas

- Identificar objetos e elementos visuais.
- Reconhecer textos em imagens.
- Descrever imagens.
- Localizar botões, campos e menus.
- Interpretar capturas de tela.
- Associar elementos visuais a ferramentas de automação.
- Analisar imagens fornecidas pelo usuário.
- Acompanhar alterações visuais durante tarefas.
- Verificar se uma automação produziu o resultado esperado.

O reconhecimento visual poderá utilizar ferramentas determinísticas e modelos especializados, com licenças verificadas.

A análise de uma imagem não significa que o Transformer linguístico tenha desenvolvido visão nativa.

---

## 9. GERAÇÃO DE IMAGENS — IMAGE CORE

A E.L.Y.S.I.A. deverá criar e editar imagens a partir de instruções e materiais autorizados.

### Habilidades desejadas

- Gerar imagens por descrição textual.
- Escolher estilos visuais.
- Selecionar proporções e resoluções.
- Produzir ilustrações e artes digitais.
- Criar imagens de apoio para vídeos.
- Gerar miniaturas para YouTube.
- Criar capas para projetos.
- Criar elementos gráficos para Instagram.
- Alterar imagens existentes.
- Remover ou substituir fundos.
- Recortar e redimensionar.
- Ajustar iluminação, nitidez e cores.
- Criar variações de uma imagem.
- Produzir elementos com transparência.
- Organizar e arquivar imagens produzidas.

### Base tecnológica

O Image Core já foi desenvolvido com uma integração local experimental ao Stable Diffusion v1.5, separado do Transformer linguístico.

Novas técnicas, como inpainting, image-to-image, upscale e controle de composição, deverão ser avaliadas conforme licenças, hardware e viabilidade.

### Metadados

Cada geração deverá registrar, quando aplicável:

- Prompt.
- Modelo.
- Versão.
- Seed.
- Resolução.
- Configuração.
- Tempo.
- Localização.
- Direitos de utilização.

**Meta:** oferecer criação de imagens utilizáveis para projetos reais, não apenas demonstrar que um modelo consegue produzir pixels.

---

## 10. PRODUÇÃO DE VÍDEOS — MEDIA STUDIO

**Referências:**

- https://github.com/calesthio/OpenMontage
- https://github.com/heygen-com/hyperframes

O Media Studio deverá permitir à E.L.Y.S.I.A. desenvolver produções audiovisuais completas.

### 10.1. Pré-produção

- Receber uma ideia.
- Pesquisar o assunto.
- Reunir fontes.
- Preparar roteiro.
- Organizar narrativa.
- Definir duração.
- Criar storyboard.
- Planejar cenas.
- Selecionar estilo visual.
- Separar materiais por cena.
- Estimar recursos e custos.
- Registrar direitos de uso dos materiais.

### 10.2. Produção

- Gerar ou selecionar imagens.
- Utilizar vídeos locais autorizados.
- Construir cenas animadas.
- Criar títulos.
- Produzir gráficos animados.
- Criar transições.
- Animar elementos SVG e HTML.
- Trabalhar com composições 2D e 3D compatíveis.
- Montar sequências.
- Combinar áudio e imagem.
- Criar vídeos explicativos.
- Produzir vídeos sem apresentador.
- Criar trailers e vinhetas.

### 10.3. Edição

- Cortar e reorganizar clipes.
- Ajustar duração.
- Sincronizar cenas.
- Trabalhar com timeline.
- Inserir trilha sonora.
- Ajustar níveis de áudio.
- Aplicar efeitos.
- Criar legendas.
- Sincronizar legendas com falas.
- Aplicar zoom, pan e movimentos.
- Criar sobreposições.
- Inserir marca-d'água.
- Preparar miniaturas.
- Gerar prévias.

### 10.4. Renderização

- Exportar MP4 e outros formatos viáveis.
- Renderizar com FFmpeg.
- Utilizar HyperFrames para composições HTML/CSS.
- Preservar parâmetros dos projetos.
- Permitir retomada quando possível.
- Verificar duração, FPS e resolução.
- Detectar falhas de áudio ou vídeo.
- Registrar resultados de renderização.

### 10.5. Tipos de conteúdo

- Vídeos educativos.
- Documentários.
- Tutoriais.
- Conteúdo de tecnologia.
- Curiosidades.
- Animações.
- Shorts.
- Reels.
- Vídeos promocionais.
- Demonstrações de software.
- Aberturas cinematográficas.
- Slides animados.
- Clipes musicais.
- Conteúdos narrados, quando houver áudio disponível.

**Prioridade:** produzir vídeos reais por composição, edição e renderização local. Geração neural de movimento original será uma capacidade adicional, sujeita a requisitos de hardware e modelos especializados.

---

## 11. ÁUDIO E MÚSICA — AUDIO STUDIO

O Audio Studio deverá ser um módulo de produção e processamento sonoro, distinto da voz conversacional do avatar.

### Habilidades desejadas

- Importar arquivos de áudio.
- Gravar áudio com autorização.
- Cortar, unir e converter arquivos.
- Reduzir ruídos.
- Ajustar volume.
- Equalizar.
- Aplicar compressão.
- Normalizar níveis.
- Adicionar efeitos sonoros.
- Misturar narração e música.
- Criar trilhas de áudio para vídeos.
- Produzir arquivos WAV, MP3 ou formatos compatíveis.
- Transcrever falas com mecanismo apropriado.
- Gerar legendas temporizadas.
- Sintetizar narração com motor de voz autorizado.
- Traduzir e preparar dublagens.
- Organizar bibliotecas de sons e músicas.
- Sincronizar música com cenas.

### Geração musical

A capacidade futura deverá incluir criação de músicas ou peças instrumentais originais por um motor específico, desde que haja tecnologia compatível, condições de uso adequadas e recursos de processamento.

O OpenMontage oferece fluxos de produção que utilizam áudio e provedores de música, mas isso não significa que seu código sozinho contenha um modelo universal de geração musical.

### Separação de módulos

**Audio Studio:** produção de arquivos sonoros.

**Voice Core:** voz, escuta e diálogo em tempo real.

O Voice Core permanece pausado até decisão de retomada.

---

## 12. VOZ E CONVERSAÇÃO FALADA — VOICE CORE

### Capacidades planejadas

- Converter texto em fala.
- Reconhecer palavras faladas.
- Reconhecer comandos de voz.
- Conversar por áudio.
- Produzir entonação natural.
- Controlar ritmo, pausas e expressividade.
- Interromper e retomar a fala.
- Sincronizar lábios e expressões do avatar.
- Detectar início e fim da fala.
- Diferenciar locutores previamente cadastrados, com consentimento.
- Integrar voz com memória e contexto.
- Preservar configurações de privacidade.

A identidade vocal deverá ser feminina, natural e coerente com a personagem.

Reconhecimento de locutores não deve ser confundido com autenticação segura suficiente para ações sensíveis.

**Situação:** módulo planejado, com desenvolvimento pausado.

---

## 13. CRIAÇÃO DE CONTEÚDO PARA REDES SOCIAIS

### Plataformas de interesse

- YouTube.
- YouTube Shorts.
- Instagram.
- Instagram Reels.
- TikTok.

### Habilidades desejadas

- Organizar ideias de conteúdo.
- Criar calendários editoriais.
- Preparar roteiros.
- Criar versões curtas e longas.
- Produzir vídeos verticais e horizontais.
- Criar capas e miniaturas.
- Preparar títulos.
- Sugerir descrições.
- Sugerir hashtags.
- Criar legendas.
- Adaptar conteúdo entre plataformas.
- Organizar projetos em séries.
- Manter identidade visual do canal.
- Preparar pacotes de publicação.
- Acompanhar arquivos publicados.
- Analisar métricas quando houver conexão autorizada.
- Comparar resultados de vídeos.
- Planejar melhorias para conteúdos futuros.

### Publicação

A E.L.Y.S.I.A. poderá futuramente utilizar APIs oficiais das plataformas para operações autorizadas.

A implementação deverá respeitar requisitos de conta, OAuth, limites das APIs, políticas e autorizações.

A criação e exportação local deverão funcionar independentemente de qualquer integração de publicação.

---

## 14. SEGURANÇA DIGITAL — SECURITY CORE

**Referência:** https://github.com/mukul975/anthropic-cybersecurity-skills

A E.L.Y.S.I.A. deverá possuir uma biblioteca de procedimentos e ferramentas para proteção de sistemas.

### Capacidades

- Revisar segurança de código.
- Identificar configurações inseguras.
- Detectar exposição acidental de credenciais.
- Verificar autenticação e controle de acesso.
- Analisar dependências.
- Revisar segurança de APIs.
- Investigar incidentes em ambientes autorizados.
- Avaliar políticas de backup.
- Testar integridade de dados.
- Identificar possíveis injeções de instruções.
- Proteger ferramentas conectadas ao Cognitive Core.
- Manter trilhas de auditoria.
- Produzir relatórios de riscos.
- Recomendar correções.
- Avaliar permissões de execução.

### Diretriz

Importar habilidades defensivas relevantes sob demanda.

Procedimentos ofensivos ou de uso dual não deverão ser executados automaticamente e dependerão de escopo e autorização adequados.

---

## 15. AVATAR 3D E INTERFACE VISUAL

A E.L.Y.S.I.A. deverá possuir uma identidade visual própria, com um avatar feminino tridimensional e animado em tempo real.

### Requisitos do avatar

- Modelo 3D real.
- Anatomia harmoniosa.
- Rig corporal.
- Rig facial.
- Cabelos com movimentos naturais.
- Respiração sutil.
- Movimentos independentes da cabeça.
- Movimentos dos ombros.
- Gestos de braços e mãos.
- Expressões faciais.
- Movimentos oculares.
- Reações ao usuário.
- Transições entre estados.
- Efeitos de partículas.
- Dissolução e reconstrução visual quando apropriado.

O avatar não deverá ser uma imagem estática com efeitos aplicados por cima.

### Intro cinematográfica

A sequência de inicialização deverá funcionar assim:

1. O aplicativo é aberto.
2. A intro cinematográfica começa.
3. A animação alcança seu clímax.
4. Ocorre uma explosão visual controlada.
5. A energia e as partículas revelam o avatar.
6. O avatar aparece de forma contínua e natural.
7. A interface principal é apresentada sem corte brusco.

### Interface principal

- Avatar como elemento central.
- Fundo predominantemente escuro.
- Identidade visual violeta.
- Interface minimalista e elegante.
- Ícones discretos para funcionalidades.
- Painéis recolhíveis.
- Caixa de texto oculta inicialmente.
- Chat aberto apenas por ação do usuário.
- Indicações discretas de estado.
- Animações suaves e não repetitivas.
- Desempenho adaptável à GPU.

### Tecnologias de interesse

Blender, modelos GLB/GLTF, Three.js, React Three Fiber, GSAP e outras ferramentas de animação adequadas.

---

## 16. DOCUMENTOS E PRODUTIVIDADE — DOCUMENT CORE

A E.L.Y.S.I.A. deverá produzir e manipular documentos.

### Capacidades

- Criar documentos DOCX.
- Criar PDFs.
- Criar planilhas XLSX.
- Criar apresentações PPTX.
- Editar arquivos existentes.
- Preencher modelos.
- Produzir relatórios.
- Criar tabelas.
- Criar gráficos.
- Construir orçamentos.
- Gerar recibos e documentos administrativos.
- Organizar arquivos.
- Extrair informações de documentos.
- Comparar versões.
- Converter formatos compatíveis.
- Arquivar resultados no Knowledge Vault.

A geração deve produzir arquivos reais e editáveis quando solicitado.

---

## 17. EDUCAÇÃO E PESQUISA — RESEARCH & LEARNING CORE

A E.L.Y.S.I.A. deverá ajudar o usuário a estudar e pesquisar utilizando materiais autorizados.

### Capacidades

- Importar apostilas.
- Organizar disciplinas.
- Buscar assuntos em livros.
- Explicar conceitos.
- Criar resumos.
- Elaborar exercícios.
- Gerar simulados.
- Corrigir questões.
- Indicar fontes e páginas.
- Organizar cronogramas de estudo.
- Acompanhar progresso.
- Produzir materiais de revisão.
- Criar apresentações educativas.
- Transformar conteúdos em vídeos explicativos.

A qualidade das explicações dependerá da competência linguística efetivamente alcançada e dos mecanismos de consulta.

A E.L.Y.S.I.A. não deve inventar referências bibliográficas.

---

## 18. FERRAMENTAS PESSOAIS E FINANCEIRAS

Além dos repositórios analisados, o ecossistema deverá permitir módulos especializados conforme as necessidades do usuário.

### Habilidades planejadas

- Organizar tarefas e compromissos.
- Gerenciar lembretes.
- Organizar projetos pessoais.
- Criar planos de estudo.
- Criar planos de treino.
- Registrar informações de exercícios.
- Organizar orçamentos.
- Simular financiamentos.
- Calcular juros e parcelas.
- Criar planilhas financeiras.
- Analisar receitas e despesas informadas.
- Consultar informações públicas.
- Pesquisar filmes, séries e serviços de streaming por integrações autorizadas.
- Recuperar histórico de atividades e decisões.

Esses recursos devem ser módulos adicionais, sem comprometer o núcleo de inteligência.

---

## 19. SISTEMA DE SKILLS E FERRAMENTAS

A E.L.Y.S.I.A. deverá possuir um registro central de habilidades.

Cada habilidade deverá informar:

- Nome.
- Descrição.
- Categoria.
- Ferramenta responsável.
- Origem.
- Licença.
- Parâmetros.
- Permissões.
- Requisitos.
- Recursos computacionais.
- Estado de disponibilidade.
- Resultados esperados.
- Testes executados.
- Limitações.
- Possibilidade de operação offline.

### Estados sugeridos

- Planejada.
- Em desenvolvimento.
- Implementada.
- Testada por simulação.
- Validada localmente.
- Validada em ambiente real.
- Bloqueada.
- Desativada.

A E.L.Y.S.I.A. não deverá anunciar uma habilidade como funcional sem demonstração correspondente.

---

## 20. REPOSITÓRIOS DE REFERÊNCIA

| Repositório | Contribuição para E.L.Y.S.I.A. |
|---|---|
| `trycua/cua` | Controle de computador, mouse, teclado e aplicativos |
| `worldflowai/everything-claude-code` | Skills, agentes e procedimentos de programação |
| `Graphify-Labs/graphify` | Grafos de conhecimento e dependências |
| `bytedance/deer-flow` | Orquestração de agentes e tarefas |
| `mukul975/anthropic-cybersecurity-skills` | Procedimentos especializados de segurança |
| `calesthio/OpenMontage` | Produção audiovisual e workflows de vídeo |
| `garrytan/gstack` | Planejamento, revisão, QA e engenharia |
| `heygen-com/hyperframes` | Animações e renderização de vídeo com HTML/CSS |

### Referências adicionais já discutidas

- `Lorran1690/elysia-2.0`: repositório principal da E.L.Y.S.I.A.
- `jingyaogong/minimind`: referência educacional de arquitetura neural, sem substituir o Transformer próprio.
- `Lorran1690/neon-aura-avatar`: referência de experimentação com o avatar.
- `Lorran1690/voice-command-life`: projeto anterior de assistente local, a preservar separadamente.
- `cardosolorran359-prog/hangar-one-hub`: projeto distinto que poderá futuramente interagir com ferramentas da E.L.Y.S.I.A. mediante integração autorizada.

Ferramentas complementares já consideradas incluem Blender, FFmpeg, ComfyUI, PyTorch, SQLite, Google Drive e Stable Diffusion v1.5.

Nenhum repositório externo deverá ser incorporado integralmente sem avaliação de arquitetura, segurança, licenciamento e redundância.

---

## 21. PRIORIDADES DE DESENVOLVIMENTO

### PRIORIDADE CRÍTICA

- Competência conversacional do Neural Core.
- Memória e recuperação confiável de conhecimento.
- Segurança e permissões.
- Integração entre Cognitive Core e ferramentas.
- Testes e evidências de funcionamento.

### PRIORIDADE ALTA

- Code Core.
- Knowledge Graph.
- Computer Control Core.
- Media Studio para criação de vídeos reais.
- Image Core.
- Produção e processamento de áudio.
- Exportação para plataformas sociais.

### PRIORIDADE INTERMEDIÁRIA

- Coordenação avançada de múltiplos agentes.
- Ferramentas especializadas de segurança.
- Análise de métricas de conteúdo.
- Geração audiovisual neural mais avançada.
- Integrações com serviços externos.
- Recursos pessoais e financeiros.

### PRIORIDADE VISUAL

- Avatar 3D natural.
- Intro cinematográfica.
- Transição por explosão.
- Interface minimalista.
- Ícones recolhíveis.
- Campo de texto oculto por padrão.
- Otimização de animações.

Essas prioridades podem avançar em paralelo quando não disputarem recursos críticos.

---

## 22. AUTONOMIA E PERMISSÕES

O proprietário concede autorização geral para atividades técnicas rotineiras de desenvolvimento, organização, execução de testes, criação de arquivos de projeto, renderização local e integração de ferramentas compatíveis.

A E.L.Y.S.I.A. deverá agir com autonomia dentro do escopo aprovado.

Entretanto, determinadas ações exigirão confirmação específica:

- Publicações públicas.
- Transações financeiras.
- Conexão de contas pessoais.
- Captura de tela e microfone.
- Compartilhamento de arquivos privados.
- Ações irreversíveis.
- Alterações sensíveis no sistema operacional.
- Atividades de segurança fora de ambientes já autorizados.

A E.L.Y.S.I.A. deverá sempre permitir interrupção, revisão e cancelamento das operações quando tecnicamente possível.

---

## 23. CRITÉRIOS DE QUALIDADE

Cada habilidade incorporada deverá ser avaliada quanto a:

1. Funcionalidade real.
2. Compatibilidade com Windows.
3. Funcionamento offline.
4. Dependência de serviços pagos.
5. Consumo de CPU, GPU, RAM e disco.
6. Segurança.
7. Licença.
8. Integração com o Cognitive Core.
9. Integração com o Knowledge Vault.
10. Facilidade de manutenção.
11. Possibilidade de cancelamento.
12. Qualidade de resultados.
13. Desempenho.
14. Testes automatizados.
15. Experiência do usuário.

O progresso do projeto deverá considerar capacidades demonstradas, e não apenas quantidade de arquivos, testes ou módulos criados.

---

## 24. VISÃO FINAL

A E.L.Y.S.I.A. deverá se tornar uma assistente capaz de receber solicitações como:

**"Elysia, crie um vídeo educativo sobre inteligência artificial."**

Ela deverá organizar o trabalho, pesquisar informações, preparar roteiro, selecionar recursos, produzir cenas, editar, renderizar e entregar os arquivos, respeitando suas capacidades reais.

**"Elysia, crie uma imagem para a miniatura do meu vídeo."**

Ela deverá utilizar o Image Core, aplicar os parâmetros solicitados, produzir o arquivo e armazená-lo.

**"Elysia, produza uma narração e sincronize com o vídeo."**

Ela deverá utilizar um motor de áudio autorizado, processar o som e integrá-lo à produção.

**"Elysia, crie um aplicativo para organizar meus projetos."**

Ela deverá utilizar o Code Core, planejar a estrutura, preparar o código, testar e apresentar as alterações para aprovação.

**"Elysia, encontre nos meus documentos tudo sobre planejamento estratégico."**

Ela deverá consultar o Knowledge Vault, recuperar os trechos relevantes e apresentar fontes.

**"Elysia, abra o programa e execute esta tarefa."**

Ela deverá utilizar o Computer Control Core respeitando permissões e condições de segurança.

**"Elysia, organize os vídeos do meu canal para o próximo mês."**

Ela deverá estruturar o calendário editorial, organizar roteiros, mídias e entregas.

---

## CONCLUSÃO DO MEMORANDO

A E.L.Y.S.I.A. 2.0 não deverá ser apenas um chatbot com plugins nem uma coleção de programas independentes.

Ela deverá ser um ecossistema integrado no qual uma inteligência central utiliza memórias, ferramentas, conhecimento e módulos especializados para realizar tarefas reais.

Seu valor será medido pela capacidade de **compreender solicitações, recuperar informações corretas, executar atividades autorizadas, produzir resultados verificáveis e melhorar progressivamente sua competência**.

O projeto deverá preservar sua identidade, seus dados, seu código e a independência do Neural Core.

**DIRETRIZ FINAL: A E.L.Y.S.I.A. DEVERÁ EVOLUIR PARA UMA ASSISTENTE PESSOAL INTELIGENTE, CRIATIVA, PRODUTIVA, MODULAR E CONFIÁVEL, CAPAZ DE TRABALHAR COM TEXTO, CÓDIGO, IMAGEM, ÁUDIO, VÍDEO, CONHECIMENTO E SISTEMAS DIGITAIS.**

**Fim do memorando.**