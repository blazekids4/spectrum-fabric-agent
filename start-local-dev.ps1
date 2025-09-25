# Start local development environment for Spectrum Fabric Agent

Write-Host "Starting local development environment..." -ForegroundColor Green

# Ensure virtual environment is activated
if (!(Test-Path env:VIRTUAL_ENV)) {
    Write-Host "Activating Python virtual environment..." -ForegroundColor Yellow
    & "$PSScriptRoot\env\Scripts\Activate.ps1"
}

# Start the development server with SWA CLI
Write-Host "Starting development servers..." -ForegroundColor Green
npm run dev