param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory=$false)]
    [int]$MaxRetries = 3,
    
    [Parameter(Mandatory=$false)]
    [int]$TimeoutInSeconds = 600
)

Write-Host "Starting deployment of Python API to Azure Function App..." -ForegroundColor Green

# Navigate to API directory
Set-Location -Path api

# Verify requirements.txt exists
if (!(Test-Path -Path "requirements.txt")) {
    Write-Host "Error: requirements.txt not found in the API directory." -ForegroundColor Red
    exit 1
}

# Check if Function App exists
Write-Host "Verifying Function App exists..." -ForegroundColor Cyan
$functionAppExists = az functionapp show --name $FunctionAppName --resource-group $ResourceGroup --query name -o tsv 2>$null

if (-not $functionAppExists) {
    Write-Host "Error: Function App '$FunctionAppName' not found in resource group '$ResourceGroup'." -ForegroundColor Red
    Write-Host "Please check the name and resource group parameters or create the Function App first." -ForegroundColor Yellow
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

# Deploy to Azure Function App with increased timeout and retry logic
Write-Host "Deploying code to Function App (this may take several minutes)..." -ForegroundColor Yellow

$retryCount = 0
$retryDelay = 30
$success = $false

# Use parameters or default values
$maxRetries = $MaxRetries
$timeout = $TimeoutInSeconds

while (-not $success -and $retryCount -lt $maxRetries) {
    if ($retryCount -gt 0) {
        Write-Host "Retry attempt $retryCount of $maxRetries after waiting $retryDelay seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds $retryDelay
        # Increase the delay for next retry (exponential backoff)
        $retryDelay = $retryDelay * 2
    }
    
    # Show progress message
    Write-Host "Uploading deployment package to Function App '$FunctionAppName'..." -ForegroundColor Cyan
    
    # Execute deployment with increased timeout
    az functionapp deployment source config-zip `
        -g $ResourceGroup `
        -n $FunctionAppName `
        --src $zipFile `
        --timeout $timeout
    
    # Check if deployment was successful
    if ($LASTEXITCODE -eq 0) {
        $success = $true
        Write-Host "Deployment successful!" -ForegroundColor Green
    } else {
        $retryCount++
        Write-Host "Deployment attempt failed with exit code $LASTEXITCODE" -ForegroundColor Yellow
        
        if ($retryCount -lt $maxRetries) {
            # Check if Function App exists and is in good state before retrying
            Write-Host "Checking Function App status before retry..." -ForegroundColor Cyan
            az functionapp show -g $ResourceGroup -n $FunctionAppName --query state -o tsv
        } else {
            Write-Host "Error: Function App deployment failed after $maxRetries attempts" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }
}

# Check final deployment state
if ($success) {
    Write-Host "Verifying deployment status..." -ForegroundColor Cyan
    $state = az functionapp show -g $ResourceGroup -n $FunctionAppName --query state -o tsv
    Write-Host "Function App state: $state" -ForegroundColor Cyan
    
    # Check if app settings are correctly set
    Write-Host "Verifying app settings..." -ForegroundColor Cyan
    az functionapp config appsettings list -g $ResourceGroup -n $FunctionAppName --query "[?name=='FUNCTIONS_EXTENSION_VERSION'].value" -o tsv

    # Clean up
    Remove-Item -Recurse -Force $tempDir
    Remove-Item -Force $zipFile

    Write-Host "Function App deployment complete!" -ForegroundColor Green
} else {
    Write-Host "Deployment failed after all retry attempts." -ForegroundColor Red
    
    # Provide troubleshooting help
    Write-Host "Troubleshooting tips:" -ForegroundColor Cyan
    Write-Host "1. Check the Function App logs: az functionapp log tail --name $FunctionAppName --resource-group $ResourceGroup" -ForegroundColor White
    Write-Host "2. Verify network connectivity to Azure" -ForegroundColor White
    Write-Host "3. Check for Azure service health issues: https://status.azure.com/" -ForegroundColor White
    Write-Host "4. Verify your Azure CLI authentication: az account show" -ForegroundColor White
    
    # Clean up temp files even on failure
    Remove-Item -Recurse -Force $tempDir
    Remove-Item -Force $zipFile
    
    exit 1
}

Set-Location -Path ..