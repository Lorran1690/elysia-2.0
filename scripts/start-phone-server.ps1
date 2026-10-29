param([string]$CoreExe, [int]$Port = 8766)
$ErrorActionPreference = 'Stop'
$privateDir = Join-Path $env:LOCALAPPDATA 'Elysia\phone-private'
New-Item -ItemType Directory -Force $privateDir | Out-Null
$keyFile = Join-Path $privateDir 'connection.key'
if ($CoreExe) {
    if (-not (Test-Path -LiteralPath $CoreExe -PathType Leaf)) { throw 'Informe o caminho do core\Elysia.exe instalado.' }
    if (-not (Test-Path -LiteralPath $keyFile)) {
        Start-Process -FilePath $CoreExe -ArgumentList @('--phone-gateway','--init-token','--token-file',('"'+$keyFile+'"')) -Wait
    }
    if (-not (Test-Path -LiteralPath $keyFile)) { throw 'Não foi possível criar a chave.' }
    Start-Process -FilePath $CoreExe -ArgumentList @('--phone-gateway','--port',"$Port",'--token-file',('"'+$keyFile+'"'))
} else {
    $projectRoot = Split-Path $PSScriptRoot -Parent
    $pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Ambiente .venv ausente. Use -CoreExe com o núcleo do aplicativo instalado.' }
    Push-Location $projectRoot
    try {
        if (-not (Test-Path -LiteralPath $keyFile)) { & $pythonExe -m interface.phone_server --init-token --token-file $keyFile; if ($LASTEXITCODE) { throw 'Falha criando chave.' } }
        Write-Host "Chave privada em $keyFile. Não compartilhe nem envie ao Git."
        & $pythonExe -m interface.phone_server --port $Port --token-file $keyFile
        if ($LASTEXITCODE) { throw 'O gateway encerrou com erro.' }
    } finally { Pop-Location }
}
