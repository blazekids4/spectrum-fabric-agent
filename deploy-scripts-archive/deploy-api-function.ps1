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

# Configure Function App settings to avoid Oryx issues
Write-Host "Configuring Function App settings to bypass Oryx build issues..." -ForegroundColor Cyan

# Check if env.json exists
if (Test-Path -Path "env.json") {
    Write-Host "Reading environment variables from env.json..." -ForegroundColor Green
    $envContent = Get-Content -Raw -Path env.json | ConvertFrom-Json
    $settingsArray = @()

    foreach ($prop in $envContent.PSObject.Properties) {
        $settingsArray += "$($prop.Name)=$($prop.Value)"
    }
} else {
    Write-Host "Warning: env.json not found. Using default settings only." -ForegroundColor Yellow
    $settingsArray = @()
}

# Add critical settings to bypass Oryx issues
$settingsArray += "FUNCTIONS_WORKER_RUNTIME=python"
$settingsArray += "FUNCTIONS_EXTENSION_VERSION=~4"
$settingsArray += "WEBSITE_RUN_FROM_PACKAGE=1"
$settingsArray += "PYTHON_ENABLE_WORKER_EXTENSIONS=1"
$settingsArray += "ENVIRONMENT=production"
$settingsArray += "SCM_DO_BUILD_DURING_DEPLOYMENT=false"  # Disable Oryx build
$settingsArray += "ENABLE_ORYX_BUILD=false"  # Explicitly disable Oryx
$settingsArray += "WEBSITE_MOUNT_ENABLED=1"
$settingsArray += "PYTHON_ISOLATE_WORKER_DEPENDENCIES=1"
$settingsArray += "AzureWebJobsFeatureFlags=EnableWorkerIndexing"

# Apply all settings at once
Write-Host "Applying Function App settings..." -ForegroundColor Green
az functionapp config appsettings set `
    --name $FunctionAppName `
    --resource-group $ResourceGroup `
    --settings $settingsArray

# Get subscription ID
$subscriptionId = az account show --query id -o tsv

# Enable managed identity for Function App
Write-Host "Enabling system-assigned managed identity for Function App..." -ForegroundColor Green
az functionapp identity assign `
    --name $FunctionAppName `
    --resource-group $ResourceGroup

# Configure scaling settings for Function App (premium plan allows this)
Write-Host "Configuring production scaling settings for Function App..." -ForegroundColor Green
az functionapp plan update `
    --name $appServicePlanName `
    --resource-group $ResourceGroup `
    --elastic-scale true `
    --max-elastic-worker-count 20

# Wait for Function App to be ready
Write-Host "Waiting for Function App to be ready..." -ForegroundColor Green
Start-Sleep -Seconds 30

# Deploy Function App Code
Write-Host "Preparing to deploy Function App code (Oryx-safe method)..." -ForegroundColor Green

# Navigate to API directory
if (!(Test-Path -Path "api")) {
    Write-Host "Error: 'api' directory not found." -ForegroundColor Red
    exit 1
}

Push-Location api

try {
    # Verify required files
    $requiredFiles = @("requirements.txt")
    foreach ($file in $requiredFiles) {
        if (!(Test-Path -Path $file)) {
            Write-Host "Error: Required file '$file' not found." -ForegroundColor Red
            Pop-Location
            exit 1
        }
    }
    
    # Create host.json if it doesn't exist
    if (!(Test-Path -Path "host.json")) {
        Write-Host "Creating host.json..." -ForegroundColor Yellow
        @"
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[3.*, 4.0.0)"
  },
  "extensions": {
    "http": {
      "routePrefix": "api"
    }
  }
}
"@ | Out-File -FilePath "host.json" -Encoding utf8
    }
    
    # Create .funcignore if it doesn't exist
    if (!(Test-Path -Path ".funcignore")) {
        Write-Host "Creating .funcignore file..." -ForegroundColor Yellow
        @"
.git*
.vscode
local.settings.json
test*
.venv/
venv/
__pycache__/
*.py[cod]
*$py.class
.Python
.python_packages
"@ | Out-File -FilePath ".funcignore" -Encoding utf8
    }
    
    # Stop Function App for clean deployment
    Write-Host "Stopping Function App for deployment..." -ForegroundColor Cyan
    az functionapp stop --name $FunctionAppName --resource-group $ResourceGroup
    
    # Create deployment package with dependencies
    Write-Host "Creating deployment package with Python dependencies..." -ForegroundColor Green
    
    # Create temp directory
    $tempDir = New-Item -ItemType Directory -Force -Path "$env:TEMP\func-deploy-$(Get-Random)"
    
    # Copy all source files (excluding .funcignore patterns)
    Write-Host "Copying source files..." -ForegroundColor Cyan
    $excludePatterns = @('.venv', '.git', '__pycache__', 'local.settings.json', 'test', '.python_packages')
    
    Get-ChildItem -Path . -Recurse | Where-Object {
        $item = $_
        $exclude = $false
        foreach ($pattern in $excludePatterns) {
            if ($item.FullName -match [regex]::Escape($pattern)) {
                $exclude = $true
                break
            }
        }
        -not $exclude
    } | ForEach-Object {
        $relativePath = $_.FullName.Substring((Get-Location).Path.Length + 1)
        $destPath = Join-Path $tempDir $relativePath
        
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Path $destPath -Force | Out-Null
        } else {
            $destDir = Split-Path $destPath -Parent
            if (!(Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            Copy-Item -Path $_.FullName -Destination $destPath -Force
        }
    }
    
    # Install Python dependencies
    Write-Host "Installing Python dependencies for deployment..." -ForegroundColor Cyan
    $libDir = Join-Path $tempDir ".python_packages\lib\site-packages"
    New-Item -ItemType Directory -Path $libDir -Force | Out-Null
    
    # Install dependencies with retry logic
    $pipRetries = 3
    $pipSuccess = $false
    for ($i = 1; $i -le $pipRetries; $i++) {
        try {
            # Try to install with platform-specific wheels first
            pip install --target=$libDir --platform linux_x86_64 --only-binary=:all: -r requirements.txt --no-deps 2>$null
            
            # Install any remaining packages
            pip install --target=$libDir -r requirements.txt --upgrade
            
            $pipSuccess = $true
            break
        } catch {
            Write-Host "Pip install attempt $i failed, retrying..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }
    
    if (-not $pipSuccess) {
        Write-Host "Failed to install Python dependencies after $pipRetries attempts" -ForegroundColor Red
        Remove-Item -Path $tempDir -Recurse -Force
        Pop-Location
        exit 1
    }
    
    # Create deployment zip
    $zipPath = Join-Path $env:TEMP "funcapp-$(Get-Date -Format 'yyyyMMddHHmmss').zip"
    Write-Host "Creating deployment package..." -ForegroundColor Cyan
    Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath -Force
    
    # Deploy with retry logic
    Write-Host "Deploying to Function App (this may take several minutes)..." -ForegroundColor Yellow
    $deployRetries = 3
    $deploySuccess = $false
    
    for ($retry = 1; $retry -le $deployRetries; $retry++) {
        if ($retry -gt 1) {
            Write-Host "Retry attempt $retry of $deployRetries..." -ForegroundColor Yellow
            Start-Sleep -Seconds 30
        }
        
        try {
            # Deploy using zip deployment
            az functionapp deployment source config-zip `
                --name $FunctionAppName `
                --resource-group $ResourceGroup `
                --src $zipPath `
                --timeout 600
            
            if ($LASTEXITCODE -eq 0) {
                $deploySuccess = $true
                break
            }
        } catch {
            Write-Host "Deployment attempt $retry failed: $_" -ForegroundColor Yellow
        }
    }
    
    # Clean up temp files
    Remove-Item -Path $tempDir -Recurse -Force
    Remove-Item -Path $zipPath -Force
    
    if (-not $deploySuccess) {
        Write-Host "Deployment failed after $deployRetries attempts" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    
    # Start Function App
    Write-Host "Starting Function App..." -ForegroundColor Cyan
    az functionapp start --name $FunctionAppName --resource-group $ResourceGroup
    
    # Wait for Function App to fully start
    Write-Host "Waiting for Function App to initialize..." -ForegroundColor Cyan
    Start-Sleep -Seconds 45
    
    # Verify deployment
    Write-Host "Verifying Function App deployment..." -ForegroundColor Green
    $functions = az functionapp function list --name $FunctionAppName --resource-group $ResourceGroup -o json | ConvertFrom-Json
    
    if ($functions.Count -gt 0) {
        Write-Host "Successfully deployed $($functions.Count) function(s):" -ForegroundColor Green
        foreach ($func in $functions) {
            Write-Host "  - $($func.name)" -ForegroundColor Cyan
        }
    } else {
        Write-Host "WARNING: No functions detected. Checking deployment logs..." -ForegroundColor Yellow
        
        # Get deployment logs
        Write-Host "Recent deployment logs:" -ForegroundColor Yellow
        az webapp log deployment show --name $FunctionAppName --resource-group $ResourceGroup --query "[-5:].{Time:time,Message:message}" -o table
        
        Write-Host "`nTroubleshooting steps:" -ForegroundColor Yellow
        Write-Host "1. Check function_app.py has proper function decorators (@app.route)" -ForegroundColor White
        Write-Host "2. Verify Python syntax: python -m py_compile function_app.py" -ForegroundColor White
        Write-Host "3. Check live logs: az functionapp log tail --name $FunctionAppName --resource-group $ResourceGroup" -ForegroundColor White
        Write-Host "4. Review Kudu console: https://$FunctionAppName.scm.azurewebsites.net" -ForegroundColor White
    }
    
} finally {
    Pop-Location
}

# Get Function App hostname
$functionAppHostname = az functionapp show --name $FunctionAppName --resource-group $ResourceGroup --query defaultHostName -o tsv

# Enable application insights for monitoring
Write-Host "Enabling application insights for monitoring..." -ForegroundColor Green
az monitor app-insights component create `
    --app "$FunctionAppName-insights" `
    --location $Location `
    --resource-group $ResourceGroup `
    --application-type web `
    --kind web

$appInsightsKey = az monitor app-insights component show `
    --app "$FunctionAppName-insights" `
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
    # Note: Direct linking isn't supported, but we'll configure CORS
    az functionapp cors add `
        --name $FunctionAppName `
        --resource-group $ResourceGroup `
        --allowed-origins "https://$StaticWebAppName.azurestaticapps.net" "https://localhost:3000"
} catch {
    Write-Host "Warning: Could not configure CORS. Please configure manually if needed." -ForegroundColor Yellow
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
    Write-Host "Error: Build output directory 'out' not found." -ForegroundColor Red
    Write-Host "Please ensure your next.config.js has 'output: export' configured." -ForegroundColor Yellow
    exit 1
}

# Get the deployment token for SWA
$token = az staticwebapp secrets list --name $StaticWebAppName --resource-group $ResourceGroup --query "properties.apiKey" -o tsv

Write-Host "Deploying to Static Web App..." -ForegroundColor Green
# Deploy using the SWA CLI with production configuration
npx @azure/static-web-apps-cli deploy --api-language python --api-version 3.11 --api-location api --app-location out --deployment-token $token --env production

# Verify deployment was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Static Web App deployment failed" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Production deployment complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Static Web App URL: https://$StaticWebAppName.azurestaticapps.net" -ForegroundColor Cyan
Write-Host "Function App URL: https://$functionAppHostname" -ForegroundColor Cyan
Write-Host "Application Insights: https://portal.azure.com/#resource/subscriptions/$subscriptionId/resourceGroups/$ResourceGroup/providers/microsoft.insights/components/$FunctionAppName-insights" -ForegroundColor Cyan
Write-Host "`nMonitor your Function App:" -ForegroundColor Yellow
Write-Host "  az functionapp log tail --name $FunctionAppName --resource-group $ResourceGroup" -ForegroundColor White