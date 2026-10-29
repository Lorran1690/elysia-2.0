# Android · interface e aplicativo

O código móvel compartilha os componentes da edição Windows, com navegação e
layout para telefone e um adaptador de módulos locais em IndexedDB. Os recursos
neural e ComfyUI não estão incluídos; não há conversação simulada.

`browser-*` registra testes no Chromium com dimensões de telefone e módulo local
real, sem servidor de respostas. Os testes de emulador e do APK de produção
assinado são etapas separadas dos workflows Android. Nenhum relatório implica
instalação no telefone do proprietário.

`preserved-files.json` registra que os renderizadores, PNGs, ícone aprovado e
checkpoint linguístico permanecem idênticos à versão anterior.
