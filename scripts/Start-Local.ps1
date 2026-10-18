param([string]$PostgresBin = 'E:\PostgreSQL\17\bin')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$runtimeDir = Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Force $runtimeDir | Out-Null
if (Test-Path '.local\postgres\PG_VERSION') {
    & (Join-Path $PostgresBin 'pg_ctl.exe') -D (Join-Path $runtimeDir 'postgres') status *> $null
    if ($LASTEXITCODE -ne 0) {
        $clusterConfig = Get-Content (Join-Path $runtimeDir 'postgres-config.json') | ConvertFrom-Json
        $clusterPort = if ($clusterConfig.port) { $clusterConfig.port } else { 55432 }
        $pgStart = Start-Process -FilePath (Join-Path $PostgresBin 'pg_ctl.exe') -ArgumentList @('-D',('"' + (Join-Path $runtimeDir 'postgres') + '"'),'-l',('"' + (Join-Path $runtimeDir 'postgres.log') + '"'),'-o',('"-h 127.0.0.1 -p ' + $clusterPort + '"'),'-w','start') -WindowStyle Hidden -Wait -PassThru
        if ($pgStart.ExitCode -ne 0) { throw 'Project PostgreSQL failed to start; inspect .local/postgres.log' }
    }
}
foreach ($port in @(8000,5173)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
        throw "Port $port is already used. Keep the existing service or run Stop-Local.ps1 for this checkout first."
    }
}
$backend = Start-Process -FilePath (Join-Path $projectRoot '.venv\Scripts\python.exe') -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'backend.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'backend.stderr.log') -PassThru
try {
    $frontend = Start-Process -FilePath (Get-Command node).Source -ArgumentList 'node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173','--strictPort' -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'frontend.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'frontend.stderr.log') -PassThru
} catch { Stop-Process -Id $backend.Id; throw }
@{ processes = @(@{id=$backend.Id; started_at=$backend.StartTime.ToUniversalTime().ToString('o')}, @{id=$frontend.Id; started_at=$frontend.StartTime.ToUniversalTime().ToString('o')}) } | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $runtimeDir 'runtime.json')
Write-Output 'Frontend: http://localhost:5173/login | API docs: http://localhost:8000/docs'
