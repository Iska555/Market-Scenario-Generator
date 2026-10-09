param(
    [string]$EvidenceDirectory = '.verification/phase8',
    [switch]$AllowDatabaseSkips
)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskPython = Join-Path $taskRoot 'backend/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run scripts/bootstrap.ps1 first.' }
if (-not $AllowDatabaseSkips -and -not $env:TEST_DATABASE_URL) {
    throw 'Acceptance requires TEST_DATABASE_URL pointing to an isolated PostgreSQL test database. -AllowDatabaseSkips is diagnostic only.'
}
$taskEvidence = [System.IO.Path]::GetFullPath((Join-Path $taskRoot $EvidenceDirectory))
New-Item -ItemType Directory -Path $taskEvidence -Force | Out-Null
$taskOldPath = $env:PATH
$taskOldCpu = $env:LOKY_MAX_CPU_COUNT
$taskResults = [System.Collections.Generic.List[object]]::new()
function Invoke-Check([string]$Name, [string]$Executable, [string[]]$Arguments) {
    $started = [DateTime]::UtcNow
    & $Executable @Arguments 2>&1 | Tee-Object -FilePath (Join-Path $taskEvidence "$Name.txt")
    $result = $LASTEXITCODE
    $taskResults.Add([pscustomobject]@{ check=$Name; exit_code=$result; seconds=([DateTime]::UtcNow-$started).TotalSeconds })
    if ($result -ne 0) { throw "$Name failed; see verification evidence." }
}
Push-Location $taskRoot
try {
    $env:PATH = "$(Split-Path $taskPython -Parent);$taskOldPath"
    $env:LOKY_MAX_CPU_COUNT = '2'
    Invoke-Check 'dependencies' $taskPython @('-m', 'pip', 'check')
    Invoke-Check 'backend' $taskPython @('-m', 'pytest')
    if (-not $AllowDatabaseSkips -and (Select-String -LiteralPath (Join-Path $taskEvidence 'backend.txt') -Pattern '\d+ skipped')) {
        throw 'Acceptance suite skipped tests; inspect PostgreSQL configuration.'
    }
    Invoke-Check 'ruff' $taskPython @('-m', 'ruff', 'check', '.')
    Invoke-Check 'format' $taskPython @('-m', 'ruff', 'format', '--check', 'backend', 'scripts')
    Invoke-Check 'mypy' $taskPython @('-m', 'mypy')
    Invoke-Check 'hooks' $taskPython @('-m', 'pre_commit', 'run', '--all-files')
    Invoke-Check 'benchmark' $taskPython @('scripts/benchmark_phase1.py')
    & $taskPython -m pip freeze | Set-Content -LiteralPath (Join-Path $taskEvidence 'resolved-python.txt') -Encoding utf8
    Push-Location frontend
    try {
        Invoke-Check 'frontend' 'npm.cmd' @('test')
        Invoke-Check 'lint' 'npm.cmd' @('run', 'lint')
        Invoke-Check 'build' 'npm.cmd' @('run', 'build')
    } finally { Pop-Location }
} finally {
    $taskResults | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskEvidence 'checks.json') -Encoding utf8
    $env:PATH = $taskOldPath
    $env:LOKY_MAX_CPU_COUNT = $taskOldCpu
    Pop-Location
}
