# Spectrum Fabric Agent - Deployment Architecture

This project uses a split deployment architecture for better performance and flexibility:

1. **Frontend**: Azure Static Web Apps
2. **Backend API**: Standalone Azure Functions (Python 3.11)

## Architecture Overview

```
┌─────────────────┐     API Requests     ┌─────────────────┐     ┌─────────────────┐
│                 │  ----------------->  │                 │     │                 │
│  Azure Static   │                      │  Azure Function │     │  Microsoft      │
│  Web App        │  <-----------------  │  App (Python)   │ --> │  Fabric         │
│  (Frontend)     │     API Responses    │  (Backend)      │     │  Integration    │
└─────────────────┘                      └─────────────────┘     └─────────────────┘
```

## Deployment Instructions

### Step 1: Deploy Backend API

Run the deployment script for the Azure Functions backend:

```powershell
./deploy-api-function.ps1
```

This will:
- Create a new Azure Functions app with Python 3.11
- Set up a storage account and Application Insights
- Enable managed identity for Microsoft Fabric access
- Configure environment variables
- Deploy the API code

### Step 2: Deploy Frontend

Run the deployment script for the Static Web App:

```powershell
./deploy-frontend-swa.ps1
```

This will:
- Create a new Static Web App
- Configure environment variables
- Connect to your GitHub repository for CI/CD
- Set up the API URL to point to your Functions App

### Step 3: Configure CORS and Security

1. In your Functions App, add your Static Web App URL to the CORS allowed origins
2. Ensure managed identity has proper permissions in Microsoft Fabric

## Local Development

1. Start the backend API:

```powershell
cd api
func start
```

2. Start the frontend:

```powershell
npm run dev
```

3. Update `.env.local` to point to your local API:

```
NEXT_PUBLIC_API_URL=http://localhost:7071
```

## Environment Variables

See `.env.example` for required environment variables.

## Important Notes

- The frontend communicates directly with the Azure Functions API
- API requests are proxied through the Static Web App configuration
- Python 3.11 is used for the backend for better performance
- Managed identity handles secure authentication to Microsoft Fabric