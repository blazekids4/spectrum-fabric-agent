# Spectrum Fabric Data Agent: Customer Deployment Guide

This guide provides step-by-step instructions for deploying the Spectrum Fabric Data Agent application in your Azure tenant. The application consists of two main components:

1. A Next.js frontend deployed as an Azure Static Web App
2. A Python API backend deployed as an Azure Function App

## Prerequisites

Before you begin, ensure you have the following:

- **Azure subscription** with permissions to create resources
- **Microsoft Fabric workspace** with appropriate access
- **Azure CLI** installed (version 2.40.0 or later)
- **Node.js** (version 22.x or later)
- **npm** (version 10.x or later)
- **Python** (version 3.11)
- **PowerShell** (version 7.x recommended)

## Step 1: Clone the Repository

```powershell
git clone https://github.com/blazekids4/spectrum-fabric-agent.git
cd spectrum-fabric-agent
```

## Step 2: Configure Environment Variables

1. Create your environment configuration file by copying the sample:

```powershell
Copy-Item env.json.sample env.json
```

2. Edit the `env.json` file with your Microsoft Fabric details:

```json
{
  "TENANT_ID": "your-azure-tenant-id",
  "DATA_AGENT_URL": "your-fabric-data-agent-url",
  "WEBSITES_PORT": "8000"
}
```

- `TENANT_ID`: Your Azure tenant ID (can be found in Azure Portal → Azure Active Directory → Properties)
- `DATA_AGENT_URL`: The URL to your Microsoft Fabric Data Agent
- `WEBSITES_PORT`: Port for the Function App (keep as 8000)

## Step 3: Install Dependencies

Install the frontend dependencies:

```powershell
npm install
```

## Step 4: Deploy the Application

The deployment process involves three main steps, all of which are automated through PowerShell scripts:

### 4.1. Create Azure Resources

This script will create all necessary Azure resources:

```powershell
./deploy_swa.ps1 -ResourceGroup "your-resource-group-name" -StaticWebAppName "your-app-name" -FunctionAppName "your-app-name-functionapp" -Location "your-preferred-region"
```

Replace the parameters with your preferred values:
- `ResourceGroup`: A new or existing resource group
- `StaticWebAppName`: Name for your Static Web App (lowercase, no spaces)
- `FunctionAppName`: Name for your Function App (lowercase, no spaces)
- `Location`: Azure region (e.g., "centralus", "eastus", "westeurope")

This script will:
- Create or use an existing Resource Group
- Create an Azure Static Web App
- Create a Storage Account for the Function App
- Create an App Service Plan (B1 tier)
- Create an Azure Function App with Python 3.11 runtime
- Enable system-assigned managed identity for the Function App
- Configure environment variables from env.json
- Set up proper CORS between the Function App and Static Web App

### 4.2. Deploy the Frontend

Deploy the Next.js frontend to Azure Static Web Apps:

```powershell
./deploy-frontend-swa.ps1 -ResourceGroup "your-resource-group-name" -StaticWebAppName "your-app-name"
```

This script will:
- Build the Next.js application
- Create static exports for Azure Static Web Apps
- Deploy the built files to your Static Web App

### 4.3. Deploy the API Backend

Deploy the Python API to Azure Functions:

```powershell
./deploy-api-function.ps1 -ResourceGroup "your-resource-group-name" -FunctionAppName "your-app-name-functionapp"
```

This script will:
- Package your Python API code
- Deploy it to your Function App
- Configure the necessary environment variables

## Step 5: Configure Managed Identity Permissions

The Function App uses a system-assigned managed identity to securely access Microsoft Fabric resources. You need to grant this identity appropriate permissions:

1. Get the managed identity principal ID:

```powershell
az functionapp identity show --name "your-app-name-functionapp" --resource-group "your-resource-group-name" --query "principalId" -o tsv
```

2. Use this principal ID to grant access in your Microsoft Fabric workspace:
   - Navigate to your Microsoft Fabric workspace
   - Go to "Access control" or "Settings" → "Access control"
   - Add a new role assignment
   - Search for the principal ID you retrieved
   - Assign appropriate roles (such as "Reader" or specific data access roles)

## Step 6: Verify Deployment

### Function App Verification

1. Check if your Function App is running:

```powershell
az functionapp show --name "your-app-name-functionapp" --resource-group "your-resource-group-name" --query "{hostname:defaultHostName, state:state}" -o json
```

The state should be "Running".

### Static Web App Verification

1. Get your Static Web App URL:

```powershell
az staticwebapp environment list --name "your-app-name" --resource-group "your-resource-group-name" --query "[?status=='Ready'].hostname" -o tsv
```

2. Open this URL in a browser to access your application.

## Troubleshooting

### 1. Static Web App Shows Default Welcome Page

If you see "Congratulations on your new site!" instead of your application:

```powershell
# Re-deploy with explicit API configuration
$token = az staticwebapp secrets list --name "your-app-name" --resource-group "your-resource-group-name" --query "properties.apiKey" -o tsv
npx @azure/static-web-apps-cli deploy out --api-language python --api-version 3.11 --api-location ./api --deployment-token $token
```

### 2. API Connection Issues

If the frontend loads but can't connect to the API:

1. Verify CORS settings:

```powershell
az functionapp cors show --name "your-app-name-functionapp" --resource-group "your-resource-group-name"
```

It should include your Static Web App domain in allowedOrigins.

2. Check that the API URL is correctly set:

```powershell
az staticwebapp appsettings list --name "your-app-name" --resource-group "your-resource-group-name"
```

It should include NEXT_PUBLIC_API_URL pointing to your Function App.

### 3. Function App Deployment Issues

If the Function App deployment fails:

```powershell
az functionapp deployment source show --name "your-app-name-functionapp" --resource-group "your-resource-group-name"
```

Check for error messages and ensure Python dependencies are compatible with Azure Functions.

### 4. Authentication Issues with Microsoft Fabric

If the application can't authenticate to Microsoft Fabric:

1. Ensure the TENANT_ID in env.json matches your Azure tenant
2. Verify the managed identity has been granted appropriate permissions in Microsoft Fabric
3. Check Function App logs for authentication errors:

```powershell
az functionapp logs tail --name "your-app-name-functionapp" --resource-group "your-resource-group-name"
```

## Advanced Configuration

### Custom Domain

To add a custom domain to your Static Web App:

1. Navigate to your Static Web App in the Azure Portal
2. Go to "Custom domains"
3. Follow the wizard to add and validate your domain

### Environment Variables

To add or modify environment variables:

```powershell
az functionapp config appsettings set --name "your-app-name-functionapp" --resource-group "your-resource-group-name" --settings "KEY=VALUE"
```

For frontend environment variables:

```powershell
az staticwebapp appsettings set --name "your-app-name" --resource-group "your-resource-group-name" --setting-names "KEY=VALUE"
```

### Scaling

The default deployment uses a B1 App Service Plan. To scale up:

```powershell
az appservice plan update --name "your-app-name-functionapp-plan" --resource-group "your-resource-group-name" --sku S1
```

## Security Considerations

- All API communications use HTTPS
- Authentication uses Azure AD through your tenant
- Sensitive configuration is stored in environment variables
- The Function App uses managed identity for secure access to Microsoft Fabric
- Static Web App restricts allowedIpRanges to AzureCloud by default

## Support and Maintenance

For additional support or to report issues:
- Create an issue on GitHub
- Contact the repository maintainers

---

This deployment guide was created to help you successfully deploy the Spectrum Fabric Data Agent in your environment. If you encounter any issues not covered in this guide, please refer to the Azure documentation or contact the repository maintainers.