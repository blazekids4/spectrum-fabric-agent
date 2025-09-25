#!/usr/bin/env pwsh
# Script to set up local development environment and test

# Check if .env file exists and load it
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Write-Host "Loading environment variables from .env file..." -ForegroundColor Green
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            if ($name -and $value) {
                [System.Environment]::SetEnvironmentVariable($name, $value, [System.EnvironmentVariableTarget]::Process)
                Write-Host "Set $name environment variable" -ForegroundColor Gray
            }
        }
    }
}

# Verify critical environment variables
$requiredVars = @(
    "FABRIC_WORKSPACE_ID", 
    "FABRIC_DATA_AGENT_NAME", 
    "TENANT_ID", 
    "FABRIC_MODEL_NAME"
)

$missingVars = $false
foreach ($var in $requiredVars) {
    if (-not [System.Environment]::GetEnvironmentVariable($var)) {
        Write-Host "Missing required environment variable: $var" -ForegroundColor Red
        $missingVars = $true
    }
}

if ($missingVars) {
    Write-Host "Please set the missing environment variables in .env file" -ForegroundColor Yellow
    exit 1
}

# Check prerequisites
Write-Host "`nVerifying prerequisites..." -ForegroundColor Cyan
$prerequisites = $true

# Check Python version
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ $pythonVersion" -ForegroundColor Green
    
    if (-not ($pythonVersion -match "Python 3\.(9|10|11)")) {
        Write-Host "  Warning: Recommended Python version is 3.9-3.11" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Python not found or not in PATH" -ForegroundColor Red
    $prerequisites = $false
}

# Check Node.js and npm
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js not found or not in PATH" -ForegroundColor Red
    $prerequisites = $false
}

try {
    $npmVersion = npm --version
    Write-Host "✓ npm $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ npm not found or not in PATH" -ForegroundColor Red
    $prerequisites = $false
}

# Check Azure Functions Core Tools
try {
    $funcVersion = func --version
    Write-Host "✓ Azure Functions Core Tools $funcVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Azure Functions Core Tools not found" -ForegroundColor Red
    Write-Host "  Please install: npm install -g azure-functions-core-tools@4" -ForegroundColor Yellow
    $prerequisites = $false
}

if (-not $prerequisites) {
    Write-Host "`nSome prerequisites are missing. Please install them and try again." -ForegroundColor Red
    exit 1
}

# Step 1: Build frontend
Write-Host "`nBuilding Next.js frontend for local development..." -ForegroundColor Cyan

# Set frontend environment variables
[System.Environment]::SetEnvironmentVariable("NEXT_PUBLIC_API_URL", "http://localhost:7071", [System.EnvironmentVariableTarget]::Process)
[System.Environment]::SetEnvironmentVariable("NODE_ENV", "development", [System.EnvironmentVariableTarget]::Process)

# Install frontend dependencies if needed
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Blue
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install npm dependencies" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# Build the frontend
Write-Host "Building Next.js application..." -ForegroundColor Blue
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Step 2: Set up Python environment and dependencies
Write-Host "`nSetting up Python environment for API..." -ForegroundColor Cyan

# Check if local.settings.json exists in api folder
$localSettingsFile = Join-Path $PSScriptRoot "api\local.settings.json"
if (-not (Test-Path $localSettingsFile)) {
    Write-Host "Creating local.settings.json..." -ForegroundColor Blue
    
    $localSettings = @{
        IsEncrypted = $false
        Values = @{
            AzureWebJobsStorage = "UseDevelopmentStorage=true"
            FUNCTIONS_WORKER_RUNTIME = "python"
            FABRIC_WORKSPACE_ID = [System.Environment]::GetEnvironmentVariable("FABRIC_WORKSPACE_ID")
            FABRIC_DATA_AGENT_NAME = [System.Environment]::GetEnvironmentVariable("FABRIC_DATA_AGENT_NAME")
            FABRIC_MODEL_NAME = [System.Environment]::GetEnvironmentVariable("FABRIC_MODEL_NAME")
            TENANT_ID = [System.Environment]::GetEnvironmentVariable("TENANT_ID")
            CORS_ALLOW_ORIGIN = "http://localhost:3000"
        }
        Host = @{
            LocalHttpPort = 7071
            CORS = "*"
        }
    }
    
    $localSettings | ConvertTo-Json -Depth 5 | Out-File $localSettingsFile
    Write-Host "Created local.settings.json" -ForegroundColor Green
}

# Enter API directory
Push-Location "api"

try {
    # Check if Python virtual environment exists
    $venvPath = ".venv"
    if (-not (Test-Path $venvPath)) {
        Write-Host "Creating Python virtual environment..." -ForegroundColor Blue
        python -m venv .venv
    }

    # Activate virtual environment
    if ($IsWindows) {
        & ".\.venv\Scripts\Activate.ps1"
    } else {
        & "./.venv/bin/activate"
    }

    # Install Python dependencies
    Write-Host "Installing Python dependencies..." -ForegroundColor Blue
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install Python dependencies" -ForegroundColor Red
        exit $LASTEXITCODE
    }

    # Validate Python syntax
    Write-Host "Validating Python syntax..." -ForegroundColor Blue
    python -m py_compile function_app.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Python syntax errors in function_app.py" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    
    # Test API
    Write-Host "`nAll checks passed! Starting local environment..." -ForegroundColor Green
    Write-Host "Starting Azure Functions API locally..." -ForegroundColor Cyan
    
    # Choose starting method based on preference:
    Write-Host "`nYou can now run the frontend and API in separate terminals:" -ForegroundColor Yellow
    Write-Host "1. Run API:     cd api && func start" -ForegroundColor White
    Write-Host "2. Run frontend: npm run dev" -ForegroundColor White
    
    Write-Host "`nOr start the functions host now in this terminal:" -ForegroundColor Yellow
    
    $startNow = Read-Host "Start Functions host now? (y/n)"
    if ($startNow -eq "y") {
        Write-Host "Starting Functions host..." -ForegroundColor Cyan
        func start
    }
} finally {
    Pop-Location
}