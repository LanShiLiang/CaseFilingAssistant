param(
    [switch]$SkipBootstrap,
    [switch]$ProductionWeb,
    [string]$LogPrefix = "dev",
    [int]$WebPort = 3000,
    [int]$ApiPort = 8000
)

. (Join-Path $PSScriptRoot "common.ps1")
# Some desktop shells inject both Path and PATH. Windows PowerShell Start-Process
# treats them as duplicate dictionary keys, so normalize to one canonical entry.
$processPath = $env:Path
Remove-Item -LiteralPath Env:PATH -ErrorAction SilentlyContinue
$env:Path = $processPath
$root = Get-RepositoryRoot
$serviceRoot = Join-Path $root "services\api"
$python = Join-Path $serviceRoot ".venv\Scripts\python.exe"
$logRoot = Join-Path $root ".artifacts\$LogPrefix"

if (-not $SkipBootstrap -and (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath (Join-Path $root "node_modules")))) {
    & (Join-Path $PSScriptRoot "bootstrap.ps1") -SkipBrowsers
}
if (-not (Test-Path -LiteralPath $python)) { throw "Backend virtualenv missing. Run pnpm bootstrap." }

New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$localRoot = Join-Path $root ".local"
New-Item -ItemType Directory -Force -Path $localRoot | Out-Null

if (-not $env:CFA_DATABASE_URL) {
    $databasePath = (Join-Path $localRoot "case_filing.db").Replace("\", "/")
    $env:CFA_DATABASE_URL = "sqlite:///$databasePath"
}
if (-not $env:CFA_STORAGE_ROOT) { $env:CFA_STORAGE_ROOT = Join-Path $localRoot "storage" }
if (-not $env:CFA_WORKER_HEARTBEAT_FILE) { $env:CFA_WORKER_HEARTBEAT_FILE = Join-Path $localRoot "worker-heartbeat" }
if (-not $env:CFA_ALLOWED_ORIGINS) {
    $env:CFA_ALLOWED_ORIGINS = "[`"http://127.0.0.1:$WebPort`"]"
}
$env:CFA_API_PORT = [string]$ApiPort
if (-not $env:CFA_INTERNAL_API_URL) { $env:CFA_INTERNAL_API_URL = "http://127.0.0.1:$ApiPort" }

Push-Location $serviceRoot
try {
    & $python -m app.entrypoints.migrate
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
}
finally {
    Pop-Location
}

$webCommand = if ($ProductionWeb) { "start" } else { "dev" }
$node = (Get-Command node.exe -ErrorAction Stop).Source
$nextCli = Join-Path $root "apps\web\node_modules\next\dist\bin\next"
$webHost = if ($ProductionWeb) { "0.0.0.0" } else { "127.0.0.1" }
$webArguments = @($nextCli, $webCommand, "--hostname", $webHost, "--port", [string]$WebPort)
$processes = @()
try {
    $processes += Start-Process -FilePath $python -ArgumentList @("-m", "app.entrypoints.api") `
        -WorkingDirectory $serviceRoot -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logRoot "api.stdout.log") `
        -RedirectStandardError (Join-Path $logRoot "api.stderr.log")
    $processes += Start-Process -FilePath $python -ArgumentList @("-m", "app.entrypoints.worker") `
        -WorkingDirectory $serviceRoot -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logRoot "worker.stdout.log") `
        -RedirectStandardError (Join-Path $logRoot "worker.stderr.log")
    $processes += Start-Process -FilePath $node -ArgumentList $webArguments `
        -WorkingDirectory (Join-Path $root "apps\web") -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logRoot "web.stdout.log") `
        -RedirectStandardError (Join-Path $logRoot "web.stderr.log")
    $processes.Id | ConvertTo-Json | Set-Content `
        -LiteralPath (Join-Path $logRoot "process-ids.json") -Encoding ASCII

    $deadline = (Get-Date).AddSeconds(90)
    do {
        try {
            $ready = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$WebPort/health" -TimeoutSec 2
            if ($ready.StatusCode -eq 200) { break }
        }
        catch { Start-Sleep -Milliseconds 500 }
        if ((Get-Date) -gt $deadline) { throw "Services were not ready in 90 seconds. See $logRoot." }
    } while ($true)

    Write-Host "Case Filing Assistant is ready: http://127.0.0.1:$WebPort" -ForegroundColor Green
    Write-Host "Logs: $logRoot. Press Ctrl+C to stop."
    while ($true) {
        $stopped = $processes | Where-Object { $_.HasExited }
        if ($stopped) { throw "A child service stopped unexpectedly. See $logRoot." }
        Start-Sleep -Seconds 1
    }
}
finally {
    foreach ($process in $processes) {
        if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    }
}
