param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName
)

Write-Host "Starting deployment of Python API to Azure Function App..." -ForegroundColor Green

# Save current location
$originalLocation = Get-Location

# Navigate to API directory
Set-Location -Path api

# Verify requirements.txt exists
if (!(Test-Path -Path "requirements.txt")) {
    Write-Host "Error: requirements.txt not found in the API directory." -ForegroundColor Red
    Set-Location -Path $originalLocation
    exit 1
}

# Create deployment package in current directory
$timestamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
$zipFile = "../function-deploy-$timestamp.zip"

# Create .funcignore file to exclude unnecessary files
@"
.venv
.git*
.vscode
local.settings.json
test
__pycache__
*.pyc
.python_packages
data_transcripts
"@ | Out-File -FilePath ".funcignore" -Encoding utf8 -Force

# Create deployment package directly (without temp directory)
Write-Host "Creating deployment package..." -ForegroundColor Green

# Use Azure CLI to package (respects .funcignore)
az functionapp deployment source config-zip `
    -g $ResourceGroup `
    -n $FunctionAppName `
    --src . `
    --build-remote true `
    --timeout 600

# Check if deployment was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Function App deployment failed with exit code $LASTEXITCODE" -ForegroundColor Red
    Set-Location -Path $originalLocation
    exit $LASTEXITCODE
}

Write-Host "Function App deployment complete!" -ForegroundColor Green
Write-Host "Checking deployment status..." -ForegroundColor Yellow

# Give it a moment to deploy
Start-Sleep -Seconds 10

# Check function app status
$appUrl = az functionapp show --name $FunctionAppName --resource-group $ResourceGroup --query "defaultHostName" -o tsv
if ($appUrl) {
    Write-Host "Function App URL: https://$appUrl" -ForegroundColor Green
}

Set-Location -Path $originalLocation