@description('Name prefix for all resources')
param name string = 'chartervip'

@description('Location for resources')
param location string = 'centralus'  // Changed to match your successful deployment

@description('App Service Plan SKU')
@allowed(['F1','B1','P1v3','P2v3'])
param sku string = 'B1'  // Changed back to B1 since it worked in portal


@description('Node version for frontend')
param nodeVersion string = '20'

@description('Python version for backend')
param pythonVersion string = '3.11'

@description('Backend startup command')
param backendStartupCommand string = 'python -m uvicorn app:app --host 0.0.0.0 --port 8000'

// Optional application settings (secure values can be added post-provision or via azd env set)
@description('Model deployment name')
param modelDeploymentName string = ''

@description('Azure OpenAI endpoint')
param azureOpenAiEndpoint string = ''

@description('Language endpoint')
param languageEndpoint string = ''

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
    tier: sku == 'F1' ? 'Free' : sku == 'B1' ? 'Basic' : 'PremiumV3'  // Updated tier logic
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
      appSettings: [
        {
          name: 'WEBSITES_PORT'
          value: '3000'
        }
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '~${nodeVersion}'
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
          name: 'MODEL_DEPLOYMENT_NAME'
          value: modelDeploymentName
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: azureOpenAiEndpoint
        }
        {
          name: 'LANGUAGE_ENDPOINT'
          value: languageEndpoint
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
}

output frontendUrl string = 'https://${frontendName}.azurewebsites.net'
output backendUrl string = 'https://${backendName}.azurewebsites.net'
output appInsightsConnectionString string = appInsights.properties.ConnectionString
