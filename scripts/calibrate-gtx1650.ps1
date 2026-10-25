param(
    [ValidateRange(2, 20)][int]$Steps = 5,
    [ValidateSet(256, 512, 1024, 2048)][int]$Context = 512,
    [ValidateSet('auto', 'fp16', 'fp32')][string]$Precision = 'auto',
    [string]$Python = '.\.venv\Scripts\python.exe'
)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    if (-not (Test-Path $Python)) {
        throw 'Python do ambiente virtual não encontrado. Crie .venv e instale as dependências com PyTorch CUDA compatível.'
    }
    $report = "reports/curriculum-v2/gtx1650-$Context-$Precision-calibration.json"
    & $Python -m learning.foundation_preflight --config configs/foundation-gtx1650.yaml --benchmark-steps $Steps --benchmark-context $Context --precision $Precision --output $report
    if ($LASTEXITCODE -ne 0) {
        throw "Calibração não concluída. Consulte $report; o script não substitui GPU por CPU."
    }
} finally {
    Pop-Location
}
