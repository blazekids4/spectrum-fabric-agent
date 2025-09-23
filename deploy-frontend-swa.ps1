param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$StaticWebAppName
)

Write-Host "Starting deployment of frontend to Azure Static Web App..." -ForegroundColor Green

# Get Function App URL for frontend configuration
$functionAppName = "$StaticWebAppName-functionapp"
$functionAppUrl = az functionapp show --name $functionAppName --resource-group $ResourceGroup --query "defaultHostName" -o tsv
if ($functionAppUrl) {
    $apiUrl = "https://$functionAppUrl/api"
    Write-Host "Setting API URL to $apiUrl" -ForegroundColor Yellow
    
    # Set environment variables for the build
    $env:NEXT_PUBLIC_API_URL = $apiUrl
    $env:PYTHON_API_URL = $apiUrl
    
    # Also update the Static Web App settings
    az staticwebapp appsettings set --name $StaticWebAppName --resource-group $ResourceGroup --setting-names "NEXT_PUBLIC_API_URL=$apiUrl" "PYTHON_API_URL=$apiUrl"
}

# Build the frontend - with Next.js 13+ app router, the export is included in the build
Write-Host "Building frontend with Next.js..." -ForegroundColor Green
npm run build

# Verify that output directory exists
if (!(Test-Path -Path "out")) {
    Write-Host "Error: Build output directory 'out' not found. The Next.js build may have failed." -ForegroundColor Red
    Write-Host "Please check that next.config.ts has 'output: 'export'' configured properly." -ForegroundColor Yellow
    exit 1
}

# Get the deployment token
$token = az staticwebapp secrets list --name $StaticWebAppName --resource-group $ResourceGroup --query "properties.apiKey" -o tsv

Write-Host "Deploying to Static Web App..." -ForegroundColor Green
# Deploy using the SWA CLI with explicit Python configuration
# This ensures the API is correctly configured as a Python app with the right version
npx @azure/static-web-apps-cli deploy --api-language python --api-version 3.11 --api-location api --app-location out --deployment-token $token

# Verify deployment was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Deployment failed with exit code $LASTEXITCODE" -ForegroundColor Red
    Write-Host "If you're seeing the default 'Congratulations on your new site' page, try running the command again." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "Frontend deployment complete!" -ForegroundColor Green