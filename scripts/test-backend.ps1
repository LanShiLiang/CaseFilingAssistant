. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-RepositoryRoot
$python = Join-Path $root "services\api\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Run pnpm bootstrap first." }

Push-Location $root
try {
    & $python -m ruff check services/api/app services/api/tests services/api/migrations
    if ($LASTEXITCODE -ne 0) { throw "Backend lint failed." }
    & $python -m pytest services/api/tests --cov=services/api/app --cov-report=term-missing
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }
}
finally {
    Pop-Location
}
