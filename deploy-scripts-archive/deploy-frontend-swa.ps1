#!/usr/bin/env pwsh
# Azure Static Web App Deployment Script

# Configuration
$resourceGroup = "your-resource-group"  # Change this to your resource group name
$location = "eastus2"                  # Change this to your preferred location
$appName = "spectrum-fabric-frontend"  # Change this to your SWA app name

Write-Host "Starting deployment of Azure Static Web App '$appName'" -ForegroundColor Green

# Create the Static Web App
Write-Host "Creating Static Web App '$appName'..." -ForegroundColor Blue
az staticwebapp create `
    --name $appName `
    --resource-group $resourceGroup `
    --location $location `
    --branch "master" `
    --app-artifact-location "out" `
    --login-with-github

# Update the environment settings with the API URL
Write-Host "Setting environment variables..." -ForegroundColor Blue
$apiUrl = Read-Host -Prompt "Enter the Azure Function API URL (e.g., https://spectrum-fabric-api.azurewebsites.net)"

az staticwebapp appsettings set `
    --name $appName `
    --resource-group $resourceGroup `
    --setting-names "NEXT_PUBLIC_API_URL=$apiUrl"

# Build and deploy the static web app manually if needed
Write-Host "Building Next.js application..." -ForegroundColor Blue
npm run build

Write-Host "✅ Deployment configuration completed!" -ForegroundColor Green
Write-Host "Once GitHub Actions are set up, your app will be deployed automatically." -ForegroundColor Cyan
Write-Host "SWA URL: https://$appName.azurestaticapps.net" -ForegroundColor Cyan