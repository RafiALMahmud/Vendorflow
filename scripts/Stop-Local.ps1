$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$statePath = Join-Path $projectRoot '.local\runtime.json'
if (Test-Path $statePath) {
    $state = Get-Content $statePath | ConvertFrom-Json
    foreach ($entry in $state.processes) {
        $running = Get-Process -Id $entry.id -ErrorAction SilentlyContinue
        if ($running -and $running.StartTime.ToUniversalTime().ToString('o') -eq $entry.started_at) {
            Stop-Process -Id $entry.id
        }
    }
}
Write-Output 'Stopped only the recorded server processes. PostgreSQL and saved data remain intact.'
