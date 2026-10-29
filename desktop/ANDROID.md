# Elysia para Android

Aplicativo Android com a interface da Elysia adaptada ao telefone: navegação
inferior, histórico recolhível, configurações para toque, teclado e rotação,
áreas seguras e visualização central de orbes e avatares. Android 7/API24 ou mais
recente, com Android System WebView atualizado. A validação usa Android 15/API35
emulado. Os avatares, orbes, ícone aprovado e músicas originais são preservados.

## Recursos locais

- Biblioteca privada em IndexedDB, busca, importação e exportação compatíveis
  com os backups do computador. Preferências e histórico importado ficam no app.
- Editor de código e modelos determinísticos, JSON, calculadora, SHA-256,
  estatísticas e inspeção estática limitada de arquivos. Nenhum código é executado.
- Composição PNG, áudio sintetizado, animação conforme codecs do WebView,
  cinema procedural existente, prévia de arquivos e três músicas instrumentais.
- Exportar abre o compartilhamento do Android, permitindo escolher Arquivos,
  Drive ou outro aplicativo instalado. Isso não é sincronização automática.

O Neural Core Python/PyTorch do computador ainda **não é executado no Android**.
A edição móvel não simula respostas de conversa. Os modelos de geração por IA,
ComfyUI e análise AST Python também não foram portados. A criação de mídia local
é a composição existente, sem prometer imagens ou vídeos neurais realistas.
Voice Core segue pausado. Não há servidor, API paga ou GPU remota por trás do APK.

## Instalação e atualização

O instalador é `Elysia-Android.apk`, publicado com o código e seus hashes em
`artifacts/android/`. Ao abrir o APK, confirme a instalação no Android. Se o
sistema solicitar, autorize o navegador/gerenciador de arquivos usado para abrir
o instalador. O pacote usa a assinatura privada persistente do projeto.

O botão Atualizar Elysia consulta o manifesto Android fixo do repositório. Só
oferece versões com número de compilação maior, sem downgrade de versão. O
download confere tamanho/SHA-256 e compara pacote, versão e certificado com o
aplicativo instalado. A instalação só abre por ação explícita e confirmação do
Android. Pode ser necessário autorizar a própria Elysia a instalar atualizações;
depois de voltar das configurações, toque em Instalar novamente.

Atualizar mantém os dados. Desinstalar ou limpar os dados do Android remove os
registros locais; exporte backups privados antes. Eles não entram no GitHub.

## Reprodução

Em `desktop/`: `npm ci`, `npm test`, `npm run build:android`, `npx cap sync android`.
O modo Android usa `.env.android`; o build Windows continua usando Tauri e o
backend original. Não copie o EXE/Python do Windows para o telefone.

O workflow `android.yml` compila o APK release sem assinatura, executa testes
Java, lint, verificações responsivas Chromium e testes de um APK debug em
emulador. Só o modo debug permite inspecionar o WebView. O APK de distribuição
tem depuração desligada. `android-signed.yml` instala e abre o APK assinado real,
confere assinatura/alinhamento e verifica reinstalação com dados preservados.

`scripts/sign-android.py` assina o release já verificado com uma chave externa ao
repositório. Chave e senhas nunca entram no GitHub ou nos artefatos de CI. O
manifesto público contém apenas hashes, certificado público e identidade do build.
A mesma chave é necessária para futuras atualizações; seu backup é privado.

Os testes emulador/telas não comprovam desempenho em todo telefone nem execução
de modelos neurais no Android. Os relatórios distinguem emulador, navegador e
pacote de produção.
