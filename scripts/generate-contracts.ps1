. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-RepositoryRoot
$python = Join-Path $root "services\api\.venv\Scripts\python.exe"
$schema = Join-Path $root "packages\contracts\openapi.json"
$generated = Join-Path $root "packages\contracts\src\generated.ts"

& $python (Join-Path $PSScriptRoot "export_openapi.py") $schema
if ($LASTEXITCODE -ne 0) { throw "OpenAPI export failed." }
& (Join-Path $root "node_modules\.bin\openapi-typescript.cmd") $schema -o $generated
if ($LASTEXITCODE -ne 0) { throw "Type generation failed." }
