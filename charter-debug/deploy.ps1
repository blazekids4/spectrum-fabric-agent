param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$StaticWebAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$FunctionAppName = ""  # Make it optional with empty default
)

Write-Host "Starting deployment of frontend to Azure Static Web App..." -ForegroundColor Green

# If FunctionAppName not provided, try to detect it
if ([string]::IsNullOrEmpty($FunctionAppName)) {
    # List all function apps in the resource group
    $functionApps = az functionapp list --resource-group $ResourceGroup --query "[].name" -o tsv
    if ($functionApps) {
        Write-Host "Found function apps in resource group:" -ForegroundColor Yellow
        Write-Host $functionApps
        # Use the first one found
        $FunctionAppName = $functionApps.Split([Environment]::NewLine)[0]
        Write-Host "Using Function App: $FunctionAppName" -ForegroundColor Green
    }
}

# Get Function App URL for frontend configuration
if (![string]::IsNullOrEmpty($FunctionAppName)) {
    $functionAppUrl = az functionapp show --name $FunctionAppName --resource-group $ResourceGroup --query "defaultHostName" -o tsv 2>$null
    if ($functionAppUrl) {
        $apiUrl = "https://$functionAppUrl"  # Remove /api suffix for now
        Write-Host "Setting API URL to $apiUrl" -ForegroundColor Yellow
        
        # Set environment variables for the build
        $env:NEXT_PUBLIC_API_URL = $apiUrl
        $env:PYTHON_API_URL = $apiUrl
        
        # Also update the Static Web App settings
        az staticwebapp appsettings set --name $StaticWebAppName --resource-group $ResourceGroup --setting-names "NEXT_PUBLIC_API_URL=$apiUrl" "PYTHON_API_URL=$apiUrl"
    } else {
        Write-Host "Warning: Could not find Function App. Proceeding without API URL configuration." -ForegroundColor Yellow
    }
}

# Clean any previous builds
if (Test-Path "out") {
    Remove-Item -Recurse -Force "out"
}

# Build the frontend
Write-Host "Building frontend with Next.js..." -ForegroundColor Green
npm run build

# Verify that output directory exists
if (!(Test-Path -Path "out")) {
    Write-Host "Error: Build output directory 'out' not found. The Next.js build may have failed." -ForegroundColor Red
    Write-Host "Please check the build errors above and ensure next.config.ts has 'output: 'export'' configured." -ForegroundColor Yellow
    exit 1
}

# Get the deployment token
$token = az staticwebapp secrets list --name $StaticWebAppName --resource-group $ResourceGroup --query "properties.apiKey" -o tsv

Write-Host "Deploying to Static Web App..." -ForegroundColor Green
# Deploy using the SWA CLI
npx @azure/static-web-apps-cli deploy --api-language python --api-version 3.11 --api-location api --app-location out --deployment-token $token

# Verify deployment was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Deployment failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Frontend deployment complete!" -ForegroundColor Green
Write-Host "Your app should be available at: https://$StaticWebAppName.azurestaticapps.net" -ForegroundColor Green