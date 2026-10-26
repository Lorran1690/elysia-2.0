# Geração por modelos de mídia

## Teste real de imagem

O backend da Elysia submeteu um workflow de difusão a ComfyUI local em CPU,
com Stable Diffusion 1.5 FP16 repackaged, sem treinar ou substituir o Neural Core.
Resultado sintético 512×512, 20 passos, seed 1650, cerca de 415 s. O Codex
inspecionou a imagem: interior com aparência fotográfica, janelas, mobiliário,
vegetação e vista externa. Isso não é revisão independente nem comprova qualidade
universal ou cenas complexas arbitrárias. Não houve geração real de vídeo.

Mesmos parâmetros e seed retornaram o arquivo existente em aproximadamente
0,005 s, sem nova difusão. Isso mede reaproveitamento, não aceleração da geração.

Origem imutável dos pesos, licença, tamanho e hashes em real-image-verification.json.
Pesos externos não foram redistribuídos no EXE/Git; estão disponíveis na origem
pública registrada. O resultado demonstrativo foi salvo privadamente no Drive.
Prompts pessoais, identificadores do Drive e arquivos do proprietário não foram
publicados. Os parâmetros públicos são um cenário sintético criado para QA.

## Aplicativo e protocolo

O EXE inclui o adaptador, interface, histórico privado e acesso aos resultados.
ComfyUI e pesos precisam estar instalados no computador. Por escolha expressa
do proprietário, geração local, sem GPU remota, conta ou serviço pago.
ComfyUI é GPL-3.0 e não foi incorporado ou redistribuído dentro da Elysia.

199 testes Python aprovados, 9 ignorados. Protocolo e navegador com motor
SIMULADO aprovados: conexão, seleção de modelo, parâmetros, download, metadados,
reutilização e cancelamento direcionado. A imagem simulada é de um pixel e não
é evidência de realismo. O teste real de difusão acima é separado.
O workflow Windows exige testar esse adaptador no EXE antes de publicar.

## Vídeo e limitações

Workflow nativo de texto para vídeo Wan 2.1 preparado a partir do exemplo
oficial. Não usa imagens de entrada; nenhum teste de vídeo neural real foi
concluído. Perfil inicial local 384×256 e 17 quadros; outros perfis até 720p
disponíveis, sem promessa de memória, velocidade ou qualidade. Não gera um
minuto contínuo nem áudio. A GTX 1650/4 GB do proprietário não foi medida.
O objetivo de vídeo complexo e realista permanece pendente de validação local.
Neural Core e Voice Core inalterados.
