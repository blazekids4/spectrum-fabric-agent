# PowerShell script for deploying Charter VIP to Azure Web Apps
Get-Content .env | ForEach-Object {
  if($_ -match '^([^#]+)=(.*)$') {
    [Environment]::SetEnvironmentVariable($matches[1], $matches[2])
  }
}
param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    `
    [Parameter(Mandatory=$true)]
    [string]$FrontendAppName,
    
    [Parameter(Mandatory=$true)]
    [string]$BackendAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "centralus"
)

Write-Host "Deploying Spectrum Demo to Azure Web Apps..." -ForegroundColor Green

# Login to Azure (if not already logged in)
Write-Host "Checking Azure login status..." -ForegroundColor Yellow
az account show 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Please login to Azure..." -ForegroundColor Yellow
    az login
}

# Create resource group if it doesn't exist
Write-Host "Creating resource group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location

# Create App Service Plan (if needed)
$appServicePlan = "$ResourceGroup-plan"
Write-Host "Creating App Service Plan..." -ForegroundColor Yellow
az appservice plan create --name $appServicePlan --resource-group $ResourceGroup --location $Location --sku B1

# Create Frontend Web App (Node.js)
Write-Host "Creating Frontend Web App..." -ForegroundColor Yellow
az webapp create --resource-group $ResourceGroup --plan $appServicePlan --name $FrontendAppName --runtime "NODE:20-lts"

# Create Backend Web App (Python)
Write-Host "Creating Backend Web App..." -ForegroundColor Yellow
az webapp create --resource-group $ResourceGroup --plan $appServicePlan --name $BackendAppName --runtime "PYTHON:3.11"

# Configure Frontend App Settings
Write-Host "Configuring Frontend App Settings..." -ForegroundColor Yellow
az webapp config appsettings set --resource-group $ResourceGroup --name $FrontendAppName --settings `
    NODE_ENV=production `
    BACKEND_URL="https://$BackendAppName.azurewebsites.net" `
    NEXT_PUBLIC_API_URL="https://$BackendAppName.azurewebsites.net"

# Configure Backend App Settings from .env file
Write-Host "Configuring Backend App Settings..." -ForegroundColor Yellow
az webapp config appsettings set --resource-group $ResourceGroup --name $BackendAppName --settings `
    TENANT_ID=$env:TENANT_ID `
    DATA_AGENT_URL=$env:DATA_AGENT_URL `
    PROJECT_ENDPOINT_MULTI_AGENT_CHARTER=$env:PROJECT_ENDPOINT_MULTI_AGENT_CHARTER `
    MODEL_ROUTER_ENDPOINT=$env:MODEL_ROUTER_ENDPOINT `
    AZURE_OPENAI_ENDPOINT=$env:AZURE_OPENAI_ENDPOINT `
    MODEL_DEPLOYMENT_NAME=$env:MODEL_DEPLOYMENT_NAME `
    LANGUAGE_KEY=$env:LANGUAGE_KEY `
    LANGUAGE_ENDPOINT=$env:LANGUAGE_ENDPOINT `
    APPLICATIONINSIGHTS_CONNECTION_STRING="$env:APPLICATIONINSIGHTS_CONNECTION_STRING"

# Configure CORS for Backend
Write-Host "Configuring CORS..." -ForegroundColor Yellow
az webapp cors add --resource-group $ResourceGroup --name $BackendAppName --allowed-origins "https://$FrontendAppName.azurewebsites.net"

# Build Frontend
Write-Host "Building Frontend..." -ForegroundColor Yellow
npm install
npm run build

# Deploy Frontend
Write-Host "Deploying Frontend..." -ForegroundColor Yellow
Compress-Archive -Path @(".next", "public", "node_modules", "package.json", "server.js", "web.config", ".env.production") -DestinationPath frontend.zip -Force
az webapp deployment source config-zip --resource-group $ResourceGroup --name $FrontendAppName --src frontend.zip
Remove-Item frontend.zip

# Deploy Backend
Write-Host "Deploying Backend..." -ForegroundColor Yellow
cd api
Compress-Archive -Path @("*.py", "requirements.txt", ".deployment", "../.env") -DestinationPath ../backend.zip -Force
cd ..
az webapp deployment source config-zip --resource-group $ResourceGroup --name $BackendAppName --src backend.zip
Remove-Item backend.zip

Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "Frontend URL: https://$FrontendAppName.azurewebsites.net" -ForegroundColor Cyan
Write-Host "Backend URL: https://$BackendAppName.azurewebsites.net" -ForegroundColor Cyan