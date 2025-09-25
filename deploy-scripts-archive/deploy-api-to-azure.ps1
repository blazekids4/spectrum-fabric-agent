param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "centralus"
)

Write-Host "Deploying simplified Azure Functions backend..." -ForegroundColor Green

# Check if Function App exists
$funcApp = az functionapp show --name $FunctionAppName --resource-group $ResourceGroup --query id -o tsv 2>$null

if (!$funcApp) {
    Write-Host "Error: Function App '$FunctionAppName' not found in resource group '$ResourceGroup'" -ForegroundColor Red
    Write-Host "Please run the main deployment script first to create the Function App." -ForegroundColor Yellow
    exit 1
}

# Navigate to API directory
Push-Location api

try {
    # Stop Function App for clean deployment
    Write-Host "Stopping Function App..." -ForegroundColor Cyan
    az functionapp stop --name $FunctionAppName --resource-group $ResourceGroup
    
    # Clean up any previous deployment artifacts
    if (Test-Path ".python_packages") {
        Remove-Item -Path ".python_packages" -Recurse -Force
    }
    
    # Create deployment package
    Write-Host "Creating deployment package..." -ForegroundColor Green
    $tempDir = New-Item -ItemType Directory -Force -Path "$env:TEMP\func-deploy-$(Get-Random)"
    
    # Copy all files
    Copy-Item -Path "*" -Destination $tempDir -Recurse -Force
    
    # Create zip
    $zipPath = Join-Path $env:TEMP "funcapp-$(Get-Date -Format 'yyyyMMddHHmmss').zip"
    Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath -Force
    
    # Deploy using zip deployment (simpler, no Oryx issues)
    Write-Host "Deploying to Azure Functions..." -ForegroundColor Yellow
    az functionapp deployment source config-zip `
        --name $FunctionAppName `
        --resource-group $ResourceGroup `
        --src $zipPath
    
    # Clean up
    Remove-Item -Path $tempDir -Recurse -Force
    Remove-Item -Path $zipPath -Force
    
    # Start Function App
    Write-Host "Starting Function App..." -ForegroundColor Cyan
    az functionapp start --name $FunctionAppName --resource-group $ResourceGroup
    
    # Wait for initialization
    Start-Sleep -Seconds 20
    
    # Verify deployment
    Write-Host "`nVerifying deployment..." -ForegroundColor Green
    $functions = az functionapp function list --name $FunctionAppName --resource-group $ResourceGroup -o json | ConvertFrom-Json
    
    if ($functions.Count -gt 0) {
        Write-Host "Successfully deployed $($functions.Count) function(s):" -ForegroundColor Green
        foreach ($func in $functions) {
            Write-Host "  - $($func.name)" -ForegroundColor Cyan
        }
        
        # Test health endpoint
        $funcUrl = az functionapp show --name $FunctionAppName --resource-group $ResourceGroup --query defaultHostName -o tsv
        Write-Host "`nTesting health endpoint..." -ForegroundColor Yellow
        try {
            $healthUrl = "https://$funcUrl/api/health"
            $response = Invoke-WebRequest -Uri $healthUrl -Method Get -TimeoutSec 10
            Write-Host "Health check passed! Status: $($response.StatusCode)" -ForegroundColor Green
        } catch {
            Write-Host "Health check endpoint not responding yet. This is normal for cold starts." -ForegroundColor Yellow
        }
    } else {
        Write-Host "Warning: No functions detected. Check logs for details." -ForegroundColor Yellow
    }
    
    Write-Host "`nDeployment complete!" -ForegroundColor Green
    Write-Host "Function App URL: https://$funcUrl" -ForegroundColor Cyan
    Write-Host "Chat endpoint: https://$funcUrl/api/chat" -ForegroundColor Cyan
    Write-Host "`nView logs: az functionapp log tail --name $FunctionAppName --resource-group $ResourceGroup" -ForegroundColor Yellow
    
} finally {
    Pop-Location
}