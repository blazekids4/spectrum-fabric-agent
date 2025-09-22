@description('Name prefix for all resources')
param name string = 'sspectrum-demo-app'

@description('Location for resources')
param location string = 'centralus'  // Changed to match your successful deployment

@description('App Service Plan SKU')
@allowed(['F1','B1','P0v3','P1v3','P2v3'])
param sku string = 'P0v3'  // Updated to P0v3

@description('Node version for frontend')
param nodeVersion string = '22'

@description('Python version for backend')
param pythonVersion string = '3.12'


@description('Backend startup command')
param backendStartupCommand string = 'cd /home/site/wwwroot && gunicorn --bind 0.0.0.0:8000 --timeout 600 --workers 1 app:app'

@description('Azure Tenant ID')
param tenantId string = ''

@description('Data Agent URL')
param dataAgentUrl string = ''

@description('Application Insights sampling rate')
param appInsightsSampling string = '5'

// Resource names
var planName = '${name}-plan'
var frontendName = '${name}-fe'
var backendName = '${name}-api'
var insightsName = '${name}-ai'

// App Service Plan
resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  sku: {
    name: sku
    tier: sku == 'F1' ? 'Free' : sku == 'B1' ? 'Basic' : 'PremiumV3'  // P0v3 uses PremiumV3 tier
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}


// Application Insights (Workspace-based optional omitted for brevity)
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: insightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    SamplingPercentage: int(appInsightsSampling)
  }
}

// Frontend Web App (Next.js)
resource frontend 'Microsoft.Web/sites@2023-12-01' = {
  name: frontendName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: plan.id
    siteConfig: {
      linuxFxVersion: 'NODE|${nodeVersion}-lts'
      appCommandLine: 'npm install && npm run build && npm start'
      appSettings: [
        {
          name: 'PORT'  // Changed from WEBSITES_PORT
          value: '8080'
        }
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '~${nodeVersion}'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '0'
        }
        {
          name: 'BACKEND_URL'
          value: 'https://${backendName}.azurewebsites.net'
        }
        {
          name: 'NEXT_PUBLIC_API_URL'
          value: 'https://${backendName}.azurewebsites.net'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
      ]
      alwaysOn: true
      ftpsState: 'Disabled'
    }
    httpsOnly: true
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: {
    'azd-service-name': 'frontend'
  }
}

// Backend Web App (FastAPI)

resource backend 'Microsoft.Web/sites@2023-12-01' = {
  name: backendName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: plan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|${pythonVersion}'
      appSettings: [
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        {
          name: 'PYTHON_ENABLE_GUNICORN_MULTIWORKERS'
          value: 'true'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: '1'
        }
        {
          name: 'STARTUP_COMMAND'
          value: backendStartupCommand
        }
        {
          name: 'TENANT_ID'
          value: tenantId
        }
        {
          name: 'DATA_AGENT_URL'
          value: dataAgentUrl
        }
        // Add these for better deployment
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '0'
        }
        {
          name: 'ENABLE_ORYX_BUILD'
          value: 'true'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
      ]
      alwaysOn: true
      ftpsState: 'Disabled'
    }
    httpsOnly: true
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: {
    'azd-service-name': 'api'  // Add this tag
  }
}

output frontendUrl string = 'https://${frontendName}.azurewebsites.net'
output backendUrl string = 'https://${backendName}.azurewebsites.net'
output appInsightsConnectionString string = appInsights.properties.ConnectionString
