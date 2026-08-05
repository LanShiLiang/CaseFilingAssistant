. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-RepositoryRoot
$runId = if ($env:CFA_E2E_RUN_ID) { $env:CFA_E2E_RUN_ID } else { "e2e-$PID" }
$databasePath = (Join-Path $root ".local\$runId.db").Replace("\", "/")
$env:CFA_DATABASE_URL = "sqlite:///$databasePath"
$env:CFA_STORAGE_ROOT = Join-Path $root ".local\$runId-storage"
$env:CFA_WORKER_HEARTBEAT_FILE = Join-Path $root ".local\$runId-heartbeat"
$env:CFA_ENVIRONMENT = "e2e"
$webPort = if ($env:CFA_E2E_WEB_PORT) { [int]$env:CFA_E2E_WEB_PORT } else { 3210 }
$apiPort = if ($env:CFA_E2E_API_PORT) { [int]$env:CFA_E2E_API_PORT } else { 8210 }
$env:CFA_ALLOWED_ORIGINS = "[`"http://127.0.0.1:$webPort`"]"
$env:CFA_INTERNAL_API_URL = "http://127.0.0.1:$apiPort"
& (Join-Path $PSScriptRoot "dev.ps1") -SkipBootstrap -ProductionWeb -LogPrefix $runId `
    -WebPort $webPort -ApiPort $apiPort
