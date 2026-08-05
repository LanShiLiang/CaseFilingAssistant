. (Join-Path $PSScriptRoot "common.ps1")
# Normalize duplicated Path/PATH before Start-Process (see dev.ps1).
$processPath = $env:Path
Remove-Item -LiteralPath Env:PATH -ErrorAction SilentlyContinue
$env:Path = $processPath

$root = Get-RepositoryRoot
$runId = "e2e-run-$PID"
$env:CFA_E2E_RUN_ID = $runId
$portOffset = $PID % 1000
$webPort = 32000 + $portOffset
$apiPort = 33000 + $portOffset
$env:CFA_E2E_WEB_PORT = [string]$webPort
$env:CFA_E2E_API_PORT = [string]$apiPort
$env:CFA_E2E_BASE_URL = "http://127.0.0.1:$webPort"
$logRoot = Join-Path $root ".artifacts\$runId"
$serverLog = Join-Path $root ".artifacts\$runId-server.log"
$server = $null

foreach ($port in @($webPort, $apiPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Stop the existing local service before E2E."
    }
}

try {
    Push-Location $root
    try { Invoke-Pnpm -Arguments @("--filter", "@case-filing/web", "build") }
    finally { Pop-Location }
    $server = Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "e2e-server.ps1")) `
        -WorkingDirectory $root -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $serverLog -RedirectStandardError "$serverLog.err"
    $deadline = (Get-Date).AddSeconds(90)
    do {
        try {
            $ready = Invoke-WebRequest -UseBasicParsing -Uri "$env:CFA_E2E_BASE_URL/health" -TimeoutSec 2
            if ($ready.StatusCode -eq 200) { break }
        }
        catch { Start-Sleep -Milliseconds 500 }
        if ($server.HasExited) { throw "E2E server stopped before readiness. See $serverLog." }
        if ((Get-Date) -gt $deadline) { throw "E2E server readiness timeout. See $serverLog." }
    } while ($true)

    & (Join-Path $root "node_modules\.bin\playwright.cmd") test
    if ($LASTEXITCODE -ne 0) { throw "Playwright acceptance failed." }
}
finally {
    $pidFile = Join-Path $logRoot "process-ids.json"
    if (Test-Path -LiteralPath $pidFile) {
        Get-Content -Raw -LiteralPath $pidFile | ConvertFrom-Json | ForEach-Object {
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
    }
    # The pnpm wrapper can spawn a Next child process. Since both ports were
    # verified free before startup, any current listeners belong to this run.
    foreach ($port in @($webPort, $apiPort)) {
        Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force }
}
