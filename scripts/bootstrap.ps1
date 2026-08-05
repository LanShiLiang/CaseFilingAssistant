param([switch]$SkipBrowsers)

. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-RepositoryRoot
$uv = Join-Path $root ".tools\uv\bin\uv.exe"

if (-not (Test-Path -LiteralPath $uv)) {
    $python = Get-BootstrapPythonInvocation
    $arguments = @($python.Prefix) + @(
        "-m", "pip", "install", "--disable-pip-version-check",
        "--target", (Join-Path $root ".tools\uv"), "uv==0.12.1"
    )
    & $python.File @arguments
    if ($LASTEXITCODE -ne 0) { throw "uv installation failed." }
}

Push-Location $root
try {
    & $uv sync --project services/api --frozen
    if ($LASTEXITCODE -ne 0) { throw "Python dependency sync failed." }
    Invoke-Pnpm -Arguments @("install", "--frozen-lockfile")
    if (-not $SkipBrowsers) {
        & (Join-Path $root "node_modules\.bin\playwright.cmd") install chromium
        if ($LASTEXITCODE -ne 0) { throw "Playwright browser installation failed." }
    }
    Write-Host "Dependencies are ready." -ForegroundColor Green
}
finally {
    Pop-Location
}
