# Qualidade de vídeo

Full HD horizontal e vertical; seleção 24/30/60 fps; bitrate proporcional; preferência VP9; até 30 segundos. Projetos anteriores continuam válidos.

Teste Chromium headless Linux/CPU: exportação Full HD VP9 decodificada no navegador e ffprobe. O exemplo de 2 segundos com 60 fps solicitados entregou apenas 21 quadros neste ambiente: resolução validada, 60 fps sustentados **não comprovados**. O navegador captura em tempo real e o desempenho depende do computador. Sem IA generativa ou áudio no vídeo.

Suite Python: 184 aprovados e 9 ignorados no primeiro processo; quatro testes HTTP foram bloqueados pelo sandbox. Reexecução do arquivo de testes HTTP com acesso à rede local: 5 aprovados, cobrindo os quatro bloqueados. Testes Node e fluxo completo de mídia no navegador aprovados, sem erros JavaScript ou solicitações externas. O teste Windows será executado pelo GitHub Actions antes da publicação.
