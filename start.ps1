[CmdletBinding()]
param([switch]$Demo)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend'
$artifactRoot = Join-Path $projectRoot 'artifacts'
$pythonExecutable = Join-Path $backendRoot '.venv\Scripts\python.exe'
$backendProcess = $null

function Assert-CommandSuccess([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE." }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/'
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw 'Install Node.js 22.18+ or 24+ first.'
}

foreach ($address in @('http://127.0.0.1:8000/api/health', 'http://127.0.0.1:5173')) {
    $occupied = $false
    try {
        $null = Invoke-WebRequest -Uri $address -TimeoutSec 2 -UseBasicParsing
        $occupied = $true
    } catch { }
    if ($occupied) { throw "A server already responds at $address. Stop it or use manual startup." }
}

New-Item -ItemType Directory -Path $artifactRoot -Force | Out-Null

Push-Location $backendRoot
try {
    & uv sync --locked --cache-dir (Join-Path $artifactRoot 'uv-cache')
    Assert-CommandSuccess 'Backend dependency installation'
    & $pythonExecutable -m alembic upgrade head
    Assert-CommandSuccess 'Database migration'
    & $pythonExecutable -m app.auth_bootstrap
    Assert-CommandSuccess 'Administrator initialization'
    if ($Demo) {
        & $pythonExecutable -m app.seed
        Assert-CommandSuccess 'Demo data initialization'
    }
} finally { Pop-Location }

Push-Location $frontendRoot
try {
    & npm ci
    Assert-CommandSuccess 'Frontend dependency installation'
} finally { Pop-Location }

try {
    $backendProcess = Start-Process -FilePath $pythonExecutable `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000' `
        -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $artifactRoot 'backend.log') `
        -RedirectStandardError (Join-Path $artifactRoot 'backend-error.log')
    $ready = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if ($backendProcess.HasExited) { throw 'Backend startup failed. See artifacts/backend-error.log.' }
        try {
            $null = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 1 -UseBasicParsing
            $ready = $true
            break
        } catch { Start-Sleep -Milliseconds 250 }
    }
    if (-not $ready) { throw 'Backend did not become ready. See artifacts/backend-error.log.' }
    Write-Host 'HRM: http://127.0.0.1:5173'
    Write-Host 'API: http://127.0.0.1:8000/api/docs'
    Write-Host 'Press Ctrl+C to stop both servers.'
    Push-Location $frontendRoot
    try {
        & npm run dev
        Assert-CommandSuccess 'Frontend server'
    } finally { Pop-Location }
} finally {
    if ($null -ne $backendProcess -and -not $backendProcess.HasExited) {
        & taskkill /PID $backendProcess.Id /T /F | Out-Null
    }
}
