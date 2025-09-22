# Spectrum Fabric Agent

A Next.js and FastAPI application that provides a chat interface to interact with Microsoft Fabric Data Agents. This application enables users to query and analyze data through a conversational interface powered by Azure AI.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Deployment Options](#deployment-options)
  - [Azure Deployment](#azure-deployment)
  - [Vercel Deployment](#vercel-deployment)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Overview

Spectrum Fabric Agent is a web application that provides a chat interface for interacting with Microsoft Fabric data. It uses a FastAPI backend to communicate with Fabric Data Agents and a Next.js frontend for the user interface. The application supports multi-turn conversations and can be deployed to Azure App Service or Vercel.

## Architecture

- **Frontend**: Next.js application with TypeScript and Tailwind CSS
- **Backend**: FastAPI Python application
- **Infrastructure**: Bicep templates for Azure deployment

## Prerequisites

- Node.js 22.x or later
- npm 10.x or later (or pnpm)
- Python 3.12 or later
- Microsoft Azure subscription (for Azure deployment)
- Microsoft Fabric workspace with Data Agent configured
- Vercel account (for Vercel deployment)

## Local Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/spectrum-fabric-agent.git
   cd spectrum-fabric-agent
   ```

2. **Set up environment variables**

   Create a `.env` file in the root directory with the following variables:

   ```env
   TENANT_ID=your-azure-tenant-id
   DATA_AGENT_URL=your-fabric-data-agent-url
   ```

   And create a `.env` file in the `api` directory with the same variables:

   ```env
   TENANT_ID=your-azure-tenant-id
   DATA_AGENT_URL=your-fabric-data-agent-url
   ```

3. **Install frontend dependencies**

   ```bash
   npm install
   # or
   pnpm install
   ```

4. **Install backend dependencies**

   ```bash
   cd api
   pip install -r requirements.txt
   cd ..
   ```

5. **Run the application locally**

   ```bash
   npm run dev
   # or
   pnpm dev
   ```

   This will start both the Next.js frontend and FastAPI backend in development mode. The application will be available at [http://localhost:3000](http://localhost:3000).

## Deployment Options

### Azure Deployment

This project includes Bicep templates for deploying to Azure App Service.

1. **Log in to Azure**

   ```bash
   az login
   ```

2. **Set your subscription**

   ```bash
   az account set --subscription <your-subscription-id>
   ```

3. **Deploy using the Azure Developer CLI (azd)**

   ```bash
   azd auth login
   azd init
   azd env set AZURE_TENANT_ID <your-tenant-id>
   azd env set DATA_AGENT_URL <your-data-agent-url>
   azd up
   ```

   Alternatively, you can use the included PowerShell script:

   ```powershell
   .\deploy-to-azure.ps1 -resourceGroupName <your-resource-group> -location <azure-region>
   ```

4. **Manual deployment**

   You can also deploy the Bicep template manually:

   ```bash
   az group create --name <your-resource-group> --location <azure-region>
   az deployment group create --resource-group <your-resource-group> --template-file infra/main.bicep --parameters tenantId=<your-tenant-id> dataAgentUrl=<your-data-agent-url>
   ```

### Vercel Deployment

1. **Install Vercel CLI**

   ```bash
   npm install -g vercel
   ```

2. **Deploy the frontend to Vercel**

   ```bash
   vercel
   ```

3. **Configure environment variables in Vercel**

   Add the following environment variables in your Vercel project settings:

   - `TENANT_ID`
   - `DATA_AGENT_URL`
   - `API_URL` (URL to your deployed API endpoint)

4. **Deploy the backend separately**

   For the backend, you'll need to deploy the FastAPI application separately. This can be done using Azure App Service or another Python hosting service.

   If using Azure App Service, follow these steps:

   ```bash
   cd api
   az webapp up --name <your-api-app-name> --resource-group <your-resource-group> --sku B1 --runtime "PYTHON:3.12"
   ```

   Then update the `API_URL` in your Vercel environment variables to point to this deployed backend.

## Environment Variables

| Name | Description | Required |
|------|-------------|----------|
| `TENANT_ID` | Azure Tenant ID | Yes |
| `DATA_AGENT_URL` | URL for the Fabric Data Agent | Yes |
| `PORT` | Port to run the Next.js server on (default: 3000) | No |

## Project Structure

```text
/
├── api/                  # FastAPI backend
│   ├── app.py            # Main FastAPI application
│   ├── fabric_agent_service.py  # Service for Fabric Data Agent interaction
│   └── requirements.txt  # Python dependencies
├── app/                  # Next.js pages and routes
├── components/           # React components
├── infra/               # Azure Bicep templates
├── public/              # Static assets
└── ...
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.