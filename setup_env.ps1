$venv = "$env:USERPROFILE\.bet_scenario_tool_venv"
$req  = Join-Path $PSScriptRoot "requirements.txt"

$ok = $false
if (Test-Path "$venv\Scripts\python.exe") {
    & "$venv\Scripts\python.exe" -c "import numpy, pandas" 2>$null
    $ok = $?
}

if (-not $ok) {
    Write-Host "==> Building environment (first run or repair)..." -ForegroundColor Cyan
    if (Test-Path $venv) { Remove-Item -Recurse -Force $venv }
    python -m venv $venv
    & "$venv\Scripts\pip.exe" install -r $req
} else {
    & "$venv\Scripts\pip.exe" install -q -r $req
}

Write-Host "==> Environment ready." -ForegroundColor Green
