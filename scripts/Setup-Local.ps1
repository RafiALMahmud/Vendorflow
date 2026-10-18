param([string]$PostgresBin, [int]$DatabasePort = 55432, [switch]$SkipOcr)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
& (Join-Path $PSScriptRoot 'Stop-Local.ps1')
if (-not $PostgresBin) {
    $pgTool = Get-Command pg_ctl -ErrorAction SilentlyContinue
    if ($pgTool) { $PostgresBin = Split-Path $pgTool.Source -Parent }
    else {
        $pgCandidates = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\pg_ctl.exe','E:\PostgreSQL\*\bin\pg_ctl.exe' -ErrorAction SilentlyContinue
        if ($pgCandidates) { $PostgresBin = Split-Path ($pgCandidates | Select-Object -Last 1).FullName -Parent }
    }
}
if (-not $PostgresBin -or -not (Test-Path (Join-Path $PostgresBin 'initdb.exe'))) {
    throw 'Install PostgreSQL 15+ or supply -PostgresBin with its bin directory. No global installer was run.'
}
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    py -3 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment creation failed' }
}
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $pythonPath -m pip install -e './backend[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Backend install failed' }
$setupArgs = @('scripts/local_environment.py','--postgres-bin',$PostgresBin,'--port',"$DatabasePort")
if ($SkipOcr) { $setupArgs += '--skip-ocr' }
& $pythonPath @setupArgs
if ($LASTEXITCODE -ne 0) { throw 'Local database/OCR setup failed; inspect .local logs' }
Push-Location backend
try {
    & $pythonPath -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Migration failed' }
} finally { Pop-Location }
Push-Location frontend
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend install failed. Stop the Vite server first if Windows reports a locked file.' }
} finally { Pop-Location }
Write-Output 'Local setup complete. Run scripts/Start-Local.ps1.'
