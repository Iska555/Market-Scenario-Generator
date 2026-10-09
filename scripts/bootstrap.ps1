param([string]$PythonExecutable = 'python')

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
Push-Location $taskRoot
try {
    $runtime = & $PythonExecutable -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
    if ($LASTEXITCODE -ne 0 -or $runtime -notin @('3.12', '3.14')) {
        throw 'Select an installed Python 3.12 or 3.14 with -PythonExecutable. Copied virtual environments must be recreated.'
    }
    & $PythonExecutable -m venv backend/.venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create backend/.venv.' }
    $taskPython = Join-Path $taskRoot 'backend/.venv/Scripts/python.exe'
    $installArgs = @('-m', 'pip', 'install', '-r', 'backend/requirements.txt', '-r', 'backend/requirements-dev.txt')
    if ($runtime -eq '3.12') {
        $installArgs += @('-c', 'backend/constraints-py312-windows.txt')
    }
    & $taskPython @installArgs
    if ($LASTEXITCODE -ne 0) { throw 'Pinned dependency installation failed.' }
    & $taskPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency failed.' }
    Push-Location frontend
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend lockfile installation failed.' }
    } finally { Pop-Location }
} finally { Pop-Location }
