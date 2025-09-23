param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName
)

Write-Host "Starting deployment of Python API to Azure Function App..." -ForegroundColor Green

# Navigate to API directory
Set-Location -Path api

# Verify requirements.txt exists
if (!(Test-Path -Path "requirements.txt")) {
    Write-Host "Error: requirements.txt not found in the API directory." -ForegroundColor Red
    exit 1
}

# Create a temporary deployment package
$tempDir = New-Item -ItemType Directory -Force -Path "$env:TEMP\function-deploy"
$zipFile = Join-Path $env:TEMP "function-$((Get-Date).ToString('yyyyMMdd-HHmmss')).zip"

# Copy all files to temp directory
Copy-Item -Path * -Destination $tempDir -Recurse -Force

# Ensure .python_packages is excluded if it exists (to prevent deployment issues)
if (Test-Path -Path "$tempDir\.python_packages") {
    Remove-Item -Recurse -Force "$tempDir\.python_packages"
}

# Create or update .funcignore file to exclude unnecessary files
@"
.venv
.git*
.vscode
local.settings.json
test
__pycache__/
.python_packages
"@ | Out-File -FilePath "$tempDir\.funcignore" -Encoding utf8 -Force

# Compress the files
Write-Host "Creating deployment package..." -ForegroundColor Green
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipFile -Force

# Deploy to Azure Function App with increased timeout
Write-Host "Deploying code to Function App (this may take a few minutes)..." -ForegroundColor Yellow
az functionapp deployment source config-zip `
    -g $ResourceGroup `
    -n $FunctionAppName `
    --src $zipFile `
    --timeout 300

# Check if deployment was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Function App deployment failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Clean up
Remove-Item -Recurse -Force $tempDir
Remove-Item -Force $zipFile

Write-Host "Function App deployment complete!" -ForegroundColor Green
Set-Location -Path ..