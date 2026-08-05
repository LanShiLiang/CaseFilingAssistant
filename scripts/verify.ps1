. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-RepositoryRoot
Push-Location $root
try {
    Invoke-Pnpm -Arguments @("lint")
    Invoke-Pnpm -Arguments @("typecheck")
    Invoke-Pnpm -Arguments @("test:web")
    & (Join-Path $PSScriptRoot "test-backend.ps1")
    & (Join-Path $PSScriptRoot "check-contracts.ps1")
    Invoke-Pnpm -Arguments @("build")
    & (Join-Path $PSScriptRoot "artifact-audit.ps1")
    Write-Host "Lint, tests, contracts, build, and artifact audit passed." -ForegroundColor Green
}
finally { Pop-Location }
