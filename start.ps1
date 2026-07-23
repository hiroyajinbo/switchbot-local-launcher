$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw ".venv was not found. Complete the setup steps in README first."
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot ".env"))) {
    throw ".env was not found. Copy .env.example and set your credentials."
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot "config.json"))) {
    throw "config.json was not found. Copy and edit config.example.json."
}

Set-Location -LiteralPath $projectRoot
& $python -m app
