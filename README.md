# Spectrum Fabric Agent – Production Deployment Guide

This project delivers a conversational experience backed by Microsoft Fabric data:

- A **Next.js** frontend hosted on **Azure Static Web Apps (SWA)**
- A **Python Azure Functions API** that connects to Fabric by using a managed identity

The `deploy-to-prod.ps1` script now provisions, deploys, and links both tiers end-to-end. Use this guide to configure the repo, run the deployment, and validate the environment.

## 1. Prerequisites

Install or verify the following locally:

- **Azure subscription** with permissions to create resource groups, Static Web Apps, and Function Apps
- **Microsoft Fabric workspace** with Data Agent configured
- **Azure CLI** ≥ 2.63 ([Install](https://docs.microsoft.com/cli/azure/install-azure-cli))
  - Static Web Apps extension: `az extension add --name staticwebapp`
- **Node.js** ≥ 22 with npm ≥ 10 ([Install](https://nodejs.org/))
- **Python** 3.11 ([Install](https://www.python.org/downloads/))
- **PowerShell** 7+ ([Install](https://docs.microsoft.com/powershell/scripting/install/installing-powershell))
- **Git** ([Install](https://git-scm.com/))

> For a detailed architecture overview, see [DEPLOYMENT.md](DEPLOYMENT.md).

## 2. Clone the repository

```powershell
git clone https://github.com/blazekids4/spectrum-fabric-agent.git
cd spectrum-fabric-agent
```

## 3. Configure backend settings (`env.json`)

Create the configuration file from the sample and populate your Fabric details:

```powershell
Copy-Item env.json.sample env.json
```

Update the placeholders with values from your Azure tenant and Fabric workspace:

```json
{
  "TENANT_ID": "00000000-0000-0000-0000-000000000000",
  "FABRIC_DATA_AGENT_NAME": "your-fabric-agent-name",
  "FABRIC_WORKSPACE_ID": "workspace-guid",
  "DATA_AGENT_URL": "https://api.fabric.microsoft.com/v1/workspaces/<workspace>/aiskills/<agent>/aiassistant/openai"
}
```

> These values are pushed into the Function App by the deployment script so the Azure Function can authenticate to Fabric.

## 4. Install frontend dependencies

```powershell
npm install
```

## 5. Run the production deployment script

`deploy-to-prod.ps1` provisions the full stack, deploys source code, links the backend to the Static Web App, and sets required configuration values.

```powershell
./deploy-to-prod.ps1 `
  -ResourceGroup "demo-charter-app6" `
  -StaticWebAppName "demo-charter-app6-fe" `
  -FunctionAppName "demo-charter-app6-be" `
  -Location "centralus"
```

What the script does:

1. Creates/updates the resource group, Static Web App (Standard SKU), storage account, premium Linux App Service plan, and Function App.
2. Pushes environment configuration from `env.json`, enforces Function App production settings (no Oryx build, managed identity enabled, HTTPS only).
3. Packages and deploys the Python API (`api/function_app.py`) via zip deployment and verifies the `/api/health` endpoint.
4. Builds the Next.js app in production mode, exports static assets, and deploys them with the SWA CLI.
5. Links the Function App to the Static Web App (SWA “Bring your own API”) and configures CORS.
6. Enables Application Insights for monitoring.

If any step fails, the script surfaces logs and troubleshooting hints—fix the issue and re-run; it is idempotent for existing resources.

## 6. Post-deployment configuration

After the script completes, confirm the production wiring:

### 6.1 Verify the SWA ↔ Function link

```powershell
az staticwebapp show `
  --name demo-charter-app6-fe `
  --resource-group demo-charter-app6 `
  --query "properties.linkedBackends"
```

Expect an entry whose `backendResourceId` points to your Function App and `provisioningState` is `Succeeded`.

### 6.2 Ensure the frontend calls the correct API host

The deployment sets the Static Web App application setting `NEXT_PUBLIC_API_URL` so the frontend’s `/api/chat` requests reach your Function App base URL.

```powershell
az staticwebapp appsettings set `
  --name demo-charter-app6-fe `
  --resource-group demo-charter-app6 `
  --setting NEXT_PUBLIC_API_URL="https://demo-charter-app6-be.azurewebsites.net"

az staticwebapp appsettings list `
  --name demo-charter-app6-fe `
  --resource-group demo-charter-app6 `
  --output table
```

> Azure CLI redacts values in the JSON output, but the setting will appear in the table.

## 7. Grant Fabric permissions to the managed identity

The Function App uses its system-assigned managed identity to call Fabric APIs. Grant it workspace access:

```powershell
$principalId = az functionapp identity show `
  --name demo-charter-app6-be `
  --resource-group demo-charter-app6 `
  --query principalId -o tsv
```

Add this principal to your Fabric workspace (Fabric → Settings → Access control) with the appropriate roles.

## 8. Validate the deployment

### 8.1 Health check

```powershell
Invoke-RestMethod https://demo-charter-app6-be.azurewebsites.net/api/health
```

Expected JSON response includes status `healthy` and Fabric metadata.

### 8.2 Frontend smoke test

1. Browse to `https://demo-charter-app6-fe.azurestaticapps.net`.
2. Use the chat interface; monitor the browser DevTools → Network tab—the `/api/chat` call should return HTTP 200 with a response payload from the Function App.

### 8.3 Live logs (optional)

```powershell
az functionapp log tail `
  --name demo-charter-app6-be `
  --resource-group demo-charter-app6
```

## 9. Troubleshooting

- **Frontend cannot reach the API:** ensure `NEXT_PUBLIC_API_URL` is set and the SWA backend link shows `Succeeded`.
- **Fabric authentication errors:** double-check the managed identity permissions and the values in `env.json`.
- **Deployment failures:** review the build output in the script or pull logs from Kudu (`https://<function-app-name>.scm.azurewebsites.net`).
- **Local testing:** run `npm run dev` to start Next.js and the Azure Function Core Tools side-by-side (`npm run func-dev`).

## 10. Ongoing maintenance

- Update environment values by editing `env.json` and re-running the deployment script (or use `az functionapp config appsettings set`).
- Add additional frontend settings with `az staticwebapp appsettings set`.
- Monitor performance and errors through the Application Insights instance created during deployment.

---

**Need help?** Open an issue on GitHub or contact the maintainers with the deployment logs from `deploy-to-prod.ps1`.