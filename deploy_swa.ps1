param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$StaticWebAppName,
    
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "centralus"
)

Write-Host "Deploying to Azure Static Web Apps..." -ForegroundColor Green

# Create Resource Group if it doesn't exist
az group create --name $ResourceGroup --location $Location

# Create Static Web App
az staticwebapp create `
    --name $StaticWebAppName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku "Standard" `
    --app-location "/"

# Create storage account for Function App (storage account name must be lowercase and unique)
$storageAccountName = $FunctionAppName.ToLower() -replace '[^a-z0-9]', ''
if ($storageAccountName.Length -gt 24) {
    $storageAccountName = $storageAccountName.Substring(0, 24)
}

# Create storage account
az storage account create `
    --name $storageAccountName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku Standard_LRS

# Create App Service plan
$appServicePlanName = "$FunctionAppName-plan"
az appservice plan create `
    --name $appServicePlanName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku B1 `
    --is-linux

# Deploy Python API as Function App
az functionapp create `
    --resource-group $ResourceGroup `
    --plan $appServicePlanName `
    --runtime python `
    --runtime-version 3.11 `
    --functions-version 4 `
    --name $FunctionAppName `
    --os-type Linux `
    --storage-account $storageAccountName

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

    # Add additional required settings
    $settingsArray += "WEBSITES_ENABLE_APP_SERVICE_STORAGE=true"
    $settingsArray += "WEBSITE_RUN_FROM_PACKAGE=1"
    $settingsArray += "FUNCTIONS_WORKER_RUNTIME=python"
    $settingsArray += "FUNCTIONS_EXTENSION_VERSION=~4"
    $settingsArray += "PYTHON_ENABLE_WORKER_EXTENSIONS=1"
    $settingsArray += "ENVIRONMENT=production"
    
    # Set SCM_DO_BUILD_DURING_DEPLOYMENT to false to prevent auto-build
    # This ensures our custom deployment process is used
    $settingsArray += "SCM_DO_BUILD_DURING_DEPLOYMENT=false"

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
        --settings WEBSITES_ENABLE_APP_SERVICE_STORAGE=true WEBSITE_RUN_FROM_PACKAGE=1 FUNCTIONS_WORKER_RUNTIME=python FUNCTIONS_EXTENSION_VERSION=~4 PYTHON_ENABLE_WORKER_EXTENSIONS=1 SCM_DO_BUILD_DURING_DEPLOYMENT=false ENVIRONMENT=production
}

# Get subscription ID
$subscriptionId = az account show --query id -o tsv

# Enable managed identity for Function App
Write-Host "Enabling system-assigned managed identity for Function App..." -ForegroundColor Green
az functionapp identity assign `
    --resource-group $ResourceGroup `
    --name $FunctionAppName

# Wait for Function App to be ready
Write-Host "Waiting for Function App to be ready..." -ForegroundColor Green
Start-Sleep -Seconds 30

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

    # First, ensure we remove any existing CORS settings to avoid duplicates
    Write-Host "Configuring CORS settings for the Function App..." -ForegroundColor Green
    
    # Clear existing CORS settings and add new ones
    az functionapp cors remove --name $FunctionAppName --resource-group $ResourceGroup --allowed-origins "*"
    
    # Add CORS settings for both the root domain and any possible preview environments
    az functionapp cors add `
        --name $FunctionAppName `
        --resource-group $ResourceGroup `
        --allowed-origins `
            "https://$($StaticWebAppName).azurestaticapps.net" `
            "https://*.$($StaticWebAppName).azurestaticapps.net" `
            "https://$($StaticWebAppName)-*.centralus.2.azurestaticapps.net" `
            "https://$($StaticWebAppName)-*.azurestaticapps.net"
    
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

Write-Host "Deployment complete!" -ForegroundColor Green