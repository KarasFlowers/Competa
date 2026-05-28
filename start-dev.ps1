[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$BackendPython = Join-Path $BackendDir ".venv\\Scripts\\python.exe"

function Write-Step {
    param([string]$Message)
    Write-Host "[Competa] $Message" -ForegroundColor Cyan
}

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-LocalPortOpen {
    param([int]$Port)

    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(300)

        if (-not $connected) {
            $client.Close()
            return $false
        }

        $null = $client.EndConnect($async)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Ensure-BackendReady {
    if (Test-Path $BackendPython) {
        Write-Step "Detected backend virtual environment in backend/.venv."
        return
    }

    if ($DryRun) {
        Write-Step "DryRun: would initialize backend/.venv and install backend dependencies."
        return
    }

    if (Test-CommandExists "uv") {
        Write-Step "backend/.venv not found. Initializing backend dependencies with uv sync."
        Push-Location $BackendDir
        try {
            & uv sync
        } finally {
            Pop-Location
        }
    } elseif (Test-CommandExists "py") {
        Write-Step "backend/.venv not found. Creating a virtual environment with py."
        Push-Location $BackendDir
        try {
            & py -3.11 -m venv .venv
            & .\.venv\Scripts\python.exe -m pip install --upgrade pip
            & .\.venv\Scripts\python.exe -m pip install -e .
        } finally {
            Pop-Location
        }
    } elseif (Test-CommandExists "python") {
        Write-Step "backend/.venv not found. Creating a virtual environment with python."
        Push-Location $BackendDir
        try {
            & python -m venv .venv
            & .\.venv\Scripts\python.exe -m pip install --upgrade pip
            & .\.venv\Scripts\python.exe -m pip install -e .
        } finally {
            Pop-Location
        }
    } else {
        throw "Could not find uv, py, or python to initialize the backend environment."
    }

    if (-not (Test-Path $BackendPython)) {
        throw "Backend environment initialization failed: $BackendPython was not created."
    }
}

function Ensure-FrontendReady {
    if (-not (Test-CommandExists "npm")) {
        throw "npm was not found. Please install Node.js first."
    }

    $nodeModulesDir = Join-Path $FrontendDir "node_modules"
    if (Test-Path $nodeModulesDir) {
        Write-Step "Detected frontend dependencies in frontend/node_modules."
        return
    }

    if ($DryRun) {
        Write-Step "DryRun: would run npm install for frontend dependencies."
        return
    }

    Write-Step "frontend/node_modules not found. Installing frontend dependencies."
    Push-Location $FrontendDir
    try {
        & npm install
    } finally {
        Pop-Location
    }
}

if (-not (Test-Path $BackendDir)) {
    throw "Backend directory not found: $BackendDir"
}

if (-not (Test-Path $FrontendDir)) {
    throw "Frontend directory not found: $FrontendDir"
}

Write-Step "Checking runtime environment..."
Ensure-BackendReady
Ensure-FrontendReady

foreach ($port in 8000, 5173) {
    if (Test-LocalPortOpen $port) {
        Write-Warning "Port $port is already in use. If startup fails, close the existing process first."
    }
}

$backendCommand = "& `"$BackendPython`" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
$frontendCommand = "npm run dev -- --host 127.0.0.1 --port 5173"

if ($DryRun) {
    Write-Step "DryRun mode enabled. Services will not be started."
    Write-Host "Backend: $backendCommand"
    Write-Host "Frontend: $frontendCommand"
    exit 0
}

Write-Step "Launching backend service window..."
Start-Process -FilePath "powershell.exe" -WorkingDirectory $BackendDir -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $backendCommand
) | Out-Null

Write-Step "Launching frontend service window..."
Start-Process -FilePath "powershell.exe" -WorkingDirectory $FrontendDir -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $frontendCommand
) | Out-Null

Write-Step "Startup commands were launched."
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "API Docs: http://127.0.0.1:8000/docs"

if (-not $NoBrowser) {
    Start-Sleep -Seconds 3
    Write-Step "Opening frontend page..."
    Start-Process "http://127.0.0.1:5173" | Out-Null
}
