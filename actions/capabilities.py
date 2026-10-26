"""Honest capability inventory: availability is distinct from neural competence."""
REFERENCE='https://github.com/Zfinix/eleven/tree/e3950adab7381a8f4a8dc11ff8a9b20b47e48c73'


def catalog():
    rows=[
      ('neural','Neural Core','experimental','Modelo próprio de diálogo disponível; conversação complexa ainda não atingida.','chat',True,'Respostas podem ser incoerentes; não há equivalência ao ChatGPT.'),
      ('vault','Knowledge Vault','parcial','Notas, TXT/Markdown, busca local e backup JSON.','library',True,'Não indexa PDFs e livros nem fornece recuperação automática ao chat; backup não criptografado.'),
      ('graph','Grafo de código','parcial','Definições, importações e nomes de chamadas de um arquivo Python.','workbench',True,'Extração sintática; sem resolução entre arquivos ou relações inferidas.'),
      ('code','Code Core','parcial','Editor, modelos iniciais, validação e revisão de diferenças.','code',True,'Não gera programas arbitrários por linguagem natural; não executa o código enviado.'),
      ('workbench','Bancada de análise · referência Eleven','implementada','Inspeção estática de PE, ELF e ZIP/APK; anotações, projetos e revisão reversível de texto.','workbench',True,'Sem Ghidra, Rizin, depurador, decompilação ou agentes ACP/MCP conectados.'),
      ('cognitive','Cognitive Core','planejada','Planejamento e execução supervisionada de tarefas compostas.',None,False,'Ainda sem orquestrador persistente ou execução autônoma de ferramentas pelo modelo.'),
      ('computer','Computer Control','planejada','Operação supervisionada de janelas e aplicativos.',None,False,'Captura, mouse e teclado não estão habilitados.'),
      ('vision','Vision Core','planejada','Reconhecimento de imagens e interfaces.',None,False,'A prévia de imagens não é reconhecimento visual.'),
      ('image','Image Core por IA','planejada','Geração e edição por modelos especializados.',None,False,'Stable Diffusion citado no memorando não está integrado neste checkout; composição PNG é outro recurso.'),
      ('media','Media Studio','parcial','PNG, projetos editáveis, animações WebM e Cinema 3D contínuo com trilha.','media',True,'Cinema é procedural; MP4 quadro a quadro ainda exige o script de produção e ferramentas fora do EXE.'),
      ('audio','Audio Studio','parcial','Tons e melodias WAV; trilha instrumental sintetizada no Cinema 3D.','media',True,'Sem editor multitrilha, transcrição, conversão geral ou geração musical por modelo.'),
      ('voice','Voice Core','pausada','Voz e escuta conversacional previstas.', 'voice',False,'Sem captura de microfone, síntese de fala ou clonagem de voz.'),
      ('social','Conteúdo e redes sociais','planejada','Calendários editoriais, pacotes e publicação autorizada.',None,False,'Não há conexão ou publicação automática em plataformas.'),
      ('security','Security Core','parcial','Hashes e inspeção de metadados sem executar arquivos.','workbench',True,'Não certifica segurança nem detecta automaticamente vulnerabilidades ou malware.'),
      ('avatar','Avatar e identidade','parcial','Interface violeta e avatar geométrico animado no Cinema 3D.','media',True,'Avatar principal ainda não é um modelo feminino natural com rig facial completo.'),
      ('documents','Document Core','planejada','DOCX, PDF, XLSX e PPTX editáveis.',None,False,'Produção desses formatos ainda não implementada no aplicativo.'),
      ('research','Pesquisa e educação','planejada','Busca com fontes, estudo e materiais de revisão.',None,False,'Sem navegador de pesquisa ou mecanismo de citações conectado ao Neural Core.'),
      ('finance','Ferramentas pessoais e financeiras','parcial','Calculadora aritmética limitada.','code',True,'Sem orçamento, transações, agenda ou integração bancária.'),
      ('skills','Registro de habilidades','implementada','Catálogo de estados, requisitos, limites e referências.','capabilities',True,'Um catálogo não implica execução da habilidade nem aprendizado neural.'),
      ('drive','Backup privado e Drive','parcial','Exportação e gravação em pasta escolhida pelo usuário.','media',True,'Pasta local não comprova sincronização. Sem OAuth/Drive direto no EXE.'),
      ('integrations','Referências e integrações','parcial','Eleven analisado como referência de bancada com revisão humana.','workbench',True,'Demais repositórios do memorando ainda dependem de análise individual e integração.')]
    result=[]
    for identifier,name,status,description,panel,offline,limitations in rows:
        result.append({'id':identifier,'name':name,'status':status,'description':description,'panel':panel,
            'offline':offline,'limitations':limitations,'category':identifier,
            'origin':REFERENCE if identifier=='workbench' else 'Elysia; memorando funcional de 26/10/2026',
            'license':'Implementação própria; licença global do projeto a definir. Eleven de referência: Apache-2.0.' if identifier=='workbench' else 'Implementação própria; dependências preservam suas licenças.',
            'parameters':'Controles do respectivo painel' if panel else 'Ainda não disponíveis',
            'permissions':'Somente operações explícitas do painel; sem execução de arquivos enviados.',
            'requirements':'Aplicativo Windows com navegador compatível' if panel else 'Implementação futura',
            'resources':'CPU; Cinema 3D se beneficia de GPU',
            'expected_output':description,'evidence':'Ver documentação da versão e relatórios públicos; estado não significa competência neural.'})
    return {'format':'elysia-capabilities-v1','reference_date':'2026-10-26','neural_weights_changed':False,'voice_core_paused':True,'capabilities':result}
