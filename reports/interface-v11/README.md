# Integração da interface v11

A interface fornecida pelo proprietário foi integrada aos módulos atuais do app.
Os dois PNGs usados pelo avatar preservam exatamente os bytes do ZIP original;
`source-manifest.json` permite conferir essa origem. Referências e prompts do ZIP
não foram incorporados ao repositório.

`source-browser.json`: teste de navegador contra o servidor real com núcleo
linguístico simulado, somente para verificar interface e rotas. Confirma a migração
de preferências, carregamento dos dois avatares, seleção corpo/busto, controles,
navegação de todos os módulos e resposta de chat pela API. Não avalia a qualidade
linguística. `avatar-body.png` é uma captura sintética dessa verificação.

A compilação Windows executa o mesmo teste contra o EXE real e também os testes
existentes de conversa/Vault/ferramentas, mídia/cinema, bancada e geração local.
A integração ComfyUI continua necessitando instalação e modelos separados. O
objetivo de vídeo neural realista permanece aberto; esta atualização não o valida.
