# Cinema 3D contínuo com música

## Artefato verificado

MP4 H.264/AAC, 60 segundos exatos, 1280×720, 30 fps e 1.800 quadros
decodificados. Áudio instrumental original sintetizado, estéreo a 48 kHz,
nível médio −14,4 dBFS e pico −2,2 dBFS (sem saturação observada).
42.063.356 bytes. SHA256 em verification.json.

Uma câmera percorre o mesmo ambiente geométrico por um minuto: avatar robótico,
núcleo em rotação, pulsos entre estações e módulos físicos. Não usa fotos,
vídeos de entrada ou sequência de slides. Os letreiros são texturas de texto
geradas localmente para as estações; não são cenas estáticas usadas como base.
É animação procedural 3D, não filmagem real ou modelo de IA generativa.

## Evidências e reprodução

- render.json: relógio determinístico da cena e estados de câmera; nenhum acesso externo.
- verification.json: ffprobe, 1.800 quadros, duração e áudio; nenhum intervalo
  congelado ou preto de pelo menos meio segundo detectado.
- browser-full-export.json: reprodução, cancelamento, geração e download
  completos de 60 s no navegador Linux. WebM decodificado com vídeo 720p e
  áudio estéreo audível; a captura em tempo real não garante 30 fps sustentados.
- windows.json: EXE real e cena/áudio/cancelamento verificados no Chromium
  Windows. Essa execução não fez o teste completo de gravação WebM de um minuto.
- Código da cena: interface/web/src/continuous-scene.js.
- MP4: scripts/render-continuous.py; verificação: scripts/verify-continuous.py.
- Reprodução no app: Vídeo → Cinema 3D · cena contínua com trilha.

O MP4 privado foi enviado ao Google Drive conforme solicitado. Identificadores
e links pessoais não são publicados no Git. Fontes e relatórios são públicos
para reprodução. O código do aplicativo empacotado é 71f0bcd28a0c; o teste
completo opcional de exportação foi acrescentado depois, sem alterar o runtime.

Pesos neurais inalterados. Não houve uso de voz, microfone ou Voice Core.
A inspeção visual foi feita pelo Codex, sem revisão humana independente.
