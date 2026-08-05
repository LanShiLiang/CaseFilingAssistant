. (Join-Path $PSScriptRoot "common.ps1")
$root = Get-RepositoryRoot
$forbiddenExtensions = @(".docx", ".pdf", ".pptx", ".key", ".pem", ".p12", ".pfx")
$runtimeRoots = @("apps", "packages", "services", "infra")
$violations = @()

foreach ($relativeRoot in $runtimeRoots) {
    $path = Join-Path $root $relativeRoot
    if (-not (Test-Path -LiteralPath $path)) { continue }
    $violations += Get-ChildItem -LiteralPath $path -Recurse -File | Where-Object {
        $_.FullName -notmatch "[\\/](node_modules|\.venv|\.next|coverage|__pycache__)[\\/]" -and
        $forbiddenExtensions -contains $_.Extension.ToLowerInvariant()
    }
}

$dockerIgnore = Join-Path $root ".dockerignore"
if (-not (Test-Path -LiteralPath $dockerIgnore)) { $violations += $dockerIgnore }
else {
    $ignoreText = Get-Content -Raw -LiteralPath $dockerIgnore
    foreach ($required in @("outputs/", ".git/", "**/*.md", "e2e/", "**/tests/")) {
        if (-not $ignoreText.Contains($required)) { $violations += ".dockerignore missing $required" }
    }
}

if ($violations.Count -gt 0) {
    $violations | ForEach-Object { Write-Error "Artifact boundary violation: $_" }
    throw "Artifact audit failed."
}
Write-Host "Artifact audit passed: runtime sources and Docker context are clean." -ForegroundColor Green
