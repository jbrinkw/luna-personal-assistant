Param(
    [int]$ChefPort = 8050,
    [int]$CoachApiPort = 3001,
    [int]$CoachUiPort = 5173,
    [int]$HubPort = 8090
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Push-Location $root

# Point Hub to the running UIs
$env:AGENT_LINKS = "ChefByte:http://localhost:$ChefPort,CoachByte:http://localhost:$CoachUiPort"

function Start-Proc {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(Mandatory=$true)][string]$Args,
        [Parameter(Mandatory=$true)][string]$WorkingDir
    )
    Start-Process -FilePath $FilePath -ArgumentList $Args -WorkingDirectory $WorkingDir -PassThru -NoNewWindow
}

$procs = @()

try {
    Write-Host "Starting ChefByte on http://localhost:$ChefPort ..."
    $pChef = Start-Proc -FilePath "python" -Args "-m uvicorn chefbyte_webapp.main:app --host 0.0.0.0 --port $ChefPort" -WorkingDir $root
    $procs += $pChef

    Write-Host "Starting CoachByte API on http://localhost:$CoachApiPort ..."
    $env:PORT = $CoachApiPort
    $pCoachApi = Start-Proc -FilePath "node" -Args "server.js" -WorkingDir (Join-Path $root "coachbyte")
    $procs += $pCoachApi

    Write-Host "Starting CoachByte UI (Vite) on http://localhost:$CoachUiPort ..."
    $coachDir = Join-Path $root "coachbyte"
    $viteBin = Join-Path $coachDir "node_modules/vite/bin/vite.js"
    if (Test-Path $viteBin) {
        $pCoachUi = Start-Proc -FilePath "node" -Args "`"$viteBin`" --port $CoachUiPort" -WorkingDir $coachDir
    } else {
        # Fallback to npx if local vite bin isn't present
        $pCoachUi = Start-Proc -FilePath "npx" -Args "--yes vite --port $CoachUiPort" -WorkingDir $coachDir
    }
    $procs += $pCoachUi

    Write-Host "Starting Hub on http://localhost:$HubPort ..."
    $pHub = Start-Proc -FilePath "python" -Args "-m uvicorn ui_hub.main:app --host 0.0.0.0 --port $HubPort" -WorkingDir $root
    $procs += $pHub

    Write-Host "`nAll servers started. Press Ctrl+C to stop."
    Wait-Process -Id ($procs | ForEach-Object { $_.Id })
}
finally {
    Write-Host "`nStopping servers..."
    foreach ($p in $procs) {
        if ($null -ne $p) {
            try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {}
        }
    }
    Pop-Location
}


