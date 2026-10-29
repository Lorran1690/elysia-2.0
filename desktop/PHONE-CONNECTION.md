# Telefone conectado ao computador

O APK passa a oferecer Configurações → Sistema → Conectar ao meu computador.
O modelo próprio e o ComfyUI continuam no computador. Isso não melhora a qualidade
do checkpoint experimental nem comprova geração neural realista.

## Computador

Com o repositório atualizado e o ambiente Python do projeto instalado:

```powershell
cd "$HOME\elysia-calibracao"
git fetch origin
git switch feature/media-creation
git pull --ff-only
.\scripts\start-phone-server.ps1
```

Alternativamente, o novo executável do núcleo aceita `--phone-gateway`:
`scripts/start-phone-server.ps1 -CoreExe 'CAMINHO\core\Elysia.exe'`.
Esse modo é separado da janela desktop e só inicia mediante ação explícita.
A chave é criada fora do projeto, em `%LOCALAPPDATA%\Elysia\phone-private\connection.key`.
Nunca envie esse arquivo ao GitHub. Para revogar o acesso, pare o gateway,
remova a chave e inicie novamente para criar outra.

O gateway escuta apenas `127.0.0.1:8766`. Conecte computador e Android à mesma
VPN privada e configure um encaminhamento **HTTPS com certificado confiável**
para esse endereço local. Uma opção é o recurso Serve do Tailscale, restrito à
sua rede privada; não use Funnel nem publique a porta no roteador. A instalação,
a conta e o endereço dessa VPN ainda precisam ser configurados no computador do
proprietário. O gateway não cria túneis nem muda firewall automaticamente.

## Android

No APK atualizado, informe o endereço HTTPS privado do computador e a chave do
arquivo. Toque em Conectar e testar. O campo de conversa aparece depois que o
núcleo responde ao diagnóstico. A geração por IA usa o mesmo painel existente,
encaminhando diagnóstico, pedidos, acompanhamento, cancelamento e arquivos ao
ComfyUI do computador. Instale/inicie esse motor e seus modelos separadamente.

A chave fica somente na memória da sessão; reconecte após fechar/reabrir o app.
Ela não entra nos backups. Conversas ficam no armazenamento privado do telefone;
os pedidos são processados pelo computador. Biblioteca, ferramentas e backups
locais não são enviados ao gateway. Arquivos gerados ficam no computador até
serem baixados; Google Drive continua dependendo de exportação/compartilhamento.

## Validação e entrega

Testes de transporte usam uma resposta **sintética explicitamente identificada**
para comprovar autenticação e limites, sem atribuir essa resposta ao modelo.
O gateway mantém o mesmo Neural Core próprio e pipeline ComfyUI existente.
A conexão no telefone do proprietário depende de configurar o computador e VPN.
Use o APK build 15 ou superior para ter este painel. O build 7 não contém
a conexão ao computador. Confira o estado dos testes no relatório phone-connection.
