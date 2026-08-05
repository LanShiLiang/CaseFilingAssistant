. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-RepositoryRoot
$python = Join-Path $root "services\api\.venv\Scripts\python.exe"
$temporary = Join-Path $root ".artifacts\contracts"
New-Item -ItemType Directory -Force -Path $temporary | Out-Null
$schema = Join-Path $temporary "openapi.json"
$generated = Join-Path $temporary "generated.ts"

& $python (Join-Path $PSScriptRoot "export_openapi.py") $schema
if ($LASTEXITCODE -ne 0) { throw "OpenAPI export failed." }
& (Join-Path $root "node_modules\.bin\openapi-typescript.cmd") $schema -o $generated
if ($LASTEXITCODE -ne 0) { throw "Type generation failed." }

$expectedSchema = Join-Path $root "packages\contracts\openapi.json"
$expectedTypes = Join-Path $root "packages\contracts\src\generated.ts"
if (-not (Test-Path $expectedSchema) -or -not (Test-Path $expectedTypes)) {
    throw "Contract snapshots are missing. Run pnpm contracts:generate."
}
if ((Get-FileHash $schema).Hash -ne (Get-FileHash $expectedSchema).Hash -or
    (Get-FileHash $generated).Hash -ne (Get-FileHash $expectedTypes).Hash) {
    throw "OpenAPI/type drift detected. Run pnpm contracts:generate and review the diff."
}
Write-Host "OpenAPI and generated types are in sync." -ForegroundColor Green
