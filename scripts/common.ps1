Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (-not $env:CI) { $env:CI = "true" }

function Get-RepositoryRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-PnpmInvocation {
    if ($env:CFA_PNPM -and (Test-Path -LiteralPath $env:CFA_PNPM)) {
        return [pscustomobject]@{ File = $env:CFA_PNPM; Prefix = @() }
    }
    $pnpm = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
    if (-not $pnpm) { $pnpm = Get-Command pnpm -ErrorAction SilentlyContinue }
    if ($pnpm) {
        return [pscustomobject]@{ File = $pnpm.Source; Prefix = @() }
    }
    $corepack = Get-Command corepack.cmd -ErrorAction SilentlyContinue
    if (-not $corepack) { $corepack = Get-Command corepack -ErrorAction SilentlyContinue }
    if ($corepack) {
        return [pscustomobject]@{ File = $corepack.Source; Prefix = @("pnpm") }
    }
    throw "pnpm/corepack was not found. Install Node.js 22 LTS first."
}

function Invoke-Pnpm {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    $invocation = Get-PnpmInvocation
    $allArguments = @($invocation.Prefix) + $Arguments
    & $invocation.File @allArguments
    if ($LASTEXITCODE -ne 0) { throw "pnpm failed with exit code $LASTEXITCODE." }
}

function Get-BootstrapPythonInvocation {
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
    if ($python) {
        return [pscustomobject]@{ File = $python.Source; Prefix = @() }
    }
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if (-not $launcher) { $launcher = Get-Command py -ErrorAction SilentlyContinue }
    if ($launcher) {
        return [pscustomobject]@{ File = $launcher.Source; Prefix = @("-3.12") }
    }
    throw "Python 3.12 was not found."
}
