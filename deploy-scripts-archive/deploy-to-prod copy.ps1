param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$StaticWebAppName,
    
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "centralus",
    
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production"
)

Write-Host "Deploying to Azure Static Web Apps for PRODUCTION..." -ForegroundColor Green

# Create Resource Group if it doesn't exist
az group create --name $ResourceGroup --location $Location

# Create Static Web App with production SKU and settings
az staticwebapp create `
    --name $StaticWebAppName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku "Standard" `
    --app-location "/" `
    --tags "Environment=Production"

# Create storage account for Function App (storage account name must be lowercase and unique)
$storageAccountName = $FunctionAppName.ToLower() -replace '[^a-z0-9]', ''
if ($storageAccountName.Length -gt 24) {
    $storageAccountName = $storageAccountName.Substring(0, 24)
}

# Create storage account with production settings (geo-redundant)
az storage account create `
    --name $storageAccountName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku Standard_GRS `
    --min-tls-version TLS1_2 `
    --https-only true `
    --tags "Environment=Production"

# Create App Service plan with premium tier for production
$appServicePlanName = "$FunctionAppName-plan"
az appservice plan create `
    --name $appServicePlanName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku P1V2 `
    --is-linux `
    --tags "Environment=Production"

# Deploy Python API as Function App
az functionapp create `
    --resource-group $ResourceGroup `
    --plan $appServicePlanName `
    --runtime python `
    --runtime-version 3.11 `
    --functions-version 4 `
    --name $FunctionAppName `
    --os-type Linux `
    --storage-account $storageAccountName `
    --tags "Environment=Production"

# Configure Function App settings
# Check if env.json exists
if (Test-Path -Path "env.json") {
    # Read env.json content and format it for az cli
    Write-Host "Reading environment variables from env.json..." -ForegroundColor Green
    $envContent = Get-Content -Raw -Path env.json | ConvertFrom-Json
    $settingsArray = @()

    foreach ($prop in $envContent.PSObject.Properties) {
        $settingsArray += "$($prop.Name)=$($prop.Value)"
    }

    # Add additional required settings for production
    $settingsArray += "WEBSITES_ENABLE_APP_SERVICE_STORAGE=true"
    $settingsArray += "WEBSITE_RUN_FROM_PACKAGE=1"
    $settingsArray += "FUNCTIONS_WORKER_RUNTIME=python"
    $settingsArray += "FUNCTIONS_EXTENSION_VERSION=~4"
    $settingsArray += "PYTHON_ENABLE_WORKER_EXTENSIONS=1"
    $settingsArray += "ENVIRONMENT=production"
    $settingsArray += "SCM_DO_BUILD_DURING_DEPLOYMENT=true"  # Changed to true
    $settingsArray += "ENABLE_ORYX_BUILD=true"  # Add this for Python builds
    $settingsArray += "SCM_ENABLE_ADDITIONAL_EXPERIMENTS_UI=true"  # Add for better diagnostics

    
    # Production specific settings
    $settingsArray += "AzureWebJobsDisableHomepage=true"
    $settingsArray += "WEBSITE_HTTPLOGGING_RETENTION_DAYS=7"

    az functionapp config appsettings set `
        --name $FunctionAppName `
        --resource-group $ResourceGroup `
        --settings $settingsArray
} else {
    Write-Host "Warning: env.json not found. Applying default settings only." -ForegroundColor Yellow
    
    # Apply mandatory settings
    az functionapp config appsettings set `
        --name $FunctionAppName `
        --resource-group $ResourceGroup `
        --settings WEBSITES_ENABLE_APP_SERVICE_STORAGE=true WEBSITE_RUN_FROM_PACKAGE=1 FUNCTIONS_WORKER_RUNTIME=python FUNCTIONS_EXTENSION_VERSION=~4 PYTHON_ENABLE_WORKER_EXTENSIONS=1 SCM_DO_BUILD_DURING_DEPLOYMENT=false ENVIRONMENT=production AzureWebJobsDisableHomepage=true WEBSITE_HTTPLOGGING_RETENTION_DAYS=7
}

# Get subscription ID
$subscriptionId = az account show --query id -o tsv

# Enable managed identity for Function App
Write-Host "Enabling system-assigned managed identity for Function App..." -ForegroundColor Green
az functionapp identity assign `
    --resource-group $ResourceGroup `
    --name $FunctionAppName

# Configure scaling settings for Function App (premium plan allows this)
Write-Host "Configuring production scaling settings for Function App..." -ForegroundColor Green
az functionapp plan update `
    --resource-group $ResourceGroup `
    --name $appServicePlanName `
    --min-instances 1 `
    --max-burst 4

# Wait for Function App to be ready
Write-Host "Waiting for Function App to be ready..." -ForegroundColor Green
Start-Sleep -Seconds 45

# Enable production monitoring and diagnostics
Write-Host "Enabling application insights for monitoring..." -ForegroundColor Green
az monitor app-insights component create `
    --app $FunctionAppName-insights `
    --location $Location `
    --resource-group $ResourceGroup `
    --application-type web

$appInsightsKey = az monitor app-insights component show `
    --app $FunctionAppName-insights `
    --resource-group $ResourceGroup `
    --query instrumentationKey `
    --output tsv

# Add Application Insights to function app
az functionapp config appsettings set `
    --name $FunctionAppName `
    --resource-group $ResourceGroup `
    --settings APPINSIGHTS_INSTRUMENTATIONKEY=$appInsightsKey

# Link Function App to Static Web App
Write-Host "Linking Function App to Static Web App..." -ForegroundColor Green
try {
    # Use the function app's default hostname for the API backend
    $functionAppHostname = az functionapp show --name $FunctionAppName --resource-group $ResourceGroup --query "defaultHostName" -o tsv

    # Configure the static web app's API settings to use the function app
    az staticwebapp appsettings set `
        --name $StaticWebAppName `
        --resource-group $ResourceGroup `
        --setting-names "NEXT_PUBLIC_API_URL=https://$functionAppHostname/api"

    # Configure CORS settings for the Function App
    Write-Host "Configuring CORS settings for the Function App..." -ForegroundColor Green
    
    # Clear existing CORS settings and add new ones
    az functionapp cors remove --name $FunctionAppName --resource-group $ResourceGroup --allowed-origins "*"
    
    # Add CORS settings for both the root domain and any possible preview environments
    # For production, we're more restrictive with CORS
    az functionapp cors add `
        --name $FunctionAppName `
        --resource-group $ResourceGroup `
        --allowed-origins `
            "https://$($StaticWebAppName).azurestaticapps.net" `
            "https://*.$($StaticWebAppName).azurestaticapps.net"
    
    Write-Host "Successfully linked Function App to Static Web App" -ForegroundColor Green
    
    # Display the managed identity information
    $identity = az functionapp identity show --name $FunctionAppName --resource-group $ResourceGroup -o json | ConvertFrom-Json
    
    Write-Host "Function App has been assigned a managed identity with:" -ForegroundColor Green
    Write-Host "  Principal ID: $($identity.principalId)" -ForegroundColor Yellow
    Write-Host "  Tenant ID: $($identity.tenantId)" -ForegroundColor Yellow
    Write-Host "Please use this Principal ID to grant access to your Microsoft Fabric resources" -ForegroundColor Green
    
} catch {
    Write-Host "Warning: Failed to link Function App to Static Web App. You may need to manually link them later." -ForegroundColor Yellow
    Write-Host $_ -ForegroundColor Red
}

# Build and deploy frontend
Write-Host "Building and deploying frontend for production..." -ForegroundColor Green

# Set environment variables for the build
$env:NEXT_PUBLIC_API_URL = "https://$functionAppHostname/api"
$env:PYTHON_API_URL = "https://$functionAppHostname/api"
$env:NODE_ENV = "production"

# Build the frontend with production optimization
Write-Host "Building frontend with Next.js in production mode..." -ForegroundColor Green
npm run build

# Verify that output directory exists
if (!(Test-Path -Path "out")) {
    Write-Host "Error: Build output directory 'out' not found. The Next.js build may have failed." -ForegroundColor Red
    Write-Host "Please check that next.config.ts has 'output: 'export'' configured properly." -ForegroundColor Yellow
    exit 1
}

# Get the deployment token for SWA
$token = az staticwebapp secrets list --name $StaticWebAppName --resource-group $ResourceGroup --query "properties.apiKey" -o tsv

Write-Host "Deploying to Static Web App..." -ForegroundColor Green
# Deploy using the SWA CLI with production configuration
npx @azure/static-web-apps-cli deploy --api-language python --api-version 3.11 --api-location api --app-location out --deployment-token $token --env production

# Verify deployment was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Deployment failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Set up custom domain if needed
# Note: This is commented out but can be uncommented and configured if needed
# Write-Host "Would you like to configure a custom domain? (y/n)" -ForegroundColor Yellow
# $configureCustomDomain = Read-Host
# if ($configureCustomDomain -eq "y") {
#     $customDomain = Read-Host "Enter your custom domain (e.g., app.example.com)"
#     az staticwebapp hostname add --name $StaticWebAppName --resource-group $ResourceGroup --hostname $customDomain
#     Write-Host "Custom domain '$customDomain' added. Please update your DNS records accordingly." -ForegroundColor Green
# }

Write-Host "Production deployment complete!" -ForegroundColor Green
Write-Host "Your Static Web App is available at: https://$($StaticWebAppName).azurestaticapps.net" -ForegroundColor Green
Write-Host "Your Function App is available at: https://$functionAppHostname" -ForegroundColor Green