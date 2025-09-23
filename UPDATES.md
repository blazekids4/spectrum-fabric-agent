# Fabric Data Agent Integration Updates

## Overview

This document details the updates made to the Spectrum Fabric Agent application to address authentication and API integration issues with Microsoft Fabric Data Agents. These changes enable the application to work correctly both in local development environments and in Azure production deployments.

## Key Changes Implemented

### 1. Authentication Improvements

- **Enhanced Authentication Flow**: Implemented a robust authentication system that supports multiple authentication methods:
  - Service Principal authentication (client ID/secret) for local development
  - Managed Identity authentication for Azure deployments
  - Azure CLI fallback for local testing
  - DefaultAzureCredential as a final fallback

- **Environment Detection**: Added logic to automatically detect Azure environments and use the appropriate authentication method.

- **Token Management**: Implemented automatic token refresh to ensure continuous operation.

### 2. API Integration Fixes

- **Assistants API Support**: Updated the client to use the Assistants API pattern, which is Microsoft's recommended approach for integrating with Fabric Data Agents.

- **Added `ask()` Method**: Implemented a simplified `ask()` method that handles the API complexity and returns just the response text.

- **URL Verification**: Added functionality to verify and test the Data Agent URL to help troubleshoot connection issues.

### 3. Error Handling and Diagnostics

- **Enhanced Error Messages**: Improved error handling with detailed diagnostic messages to aid in troubleshooting.

- **Fallback Mechanisms**: Implemented fallback API call mechanisms to increase reliability.

- **Logging**: Added comprehensive logging to help diagnose issues in both development and production.

## Production Configuration Requirements

To ensure the application works correctly in production, the following configurations are required:

### Azure Function App Configuration

1. **Enable Managed Identity**:
   - In the Azure Portal, navigate to your Function App
   - Go to "Identity" under Settings
   - Enable either System-assigned managed identity or User-assigned managed identity

2. **Configure Application Settings**:
   Set the following environment variables in the Function App Configuration:

   ```bash
   TENANT_ID=<your-azure-tenant-id>
   DATA_AGENT_URL=<your-fabric-data-agent-published-url>
   ```

   If using User-assigned managed identity:

   ```bash
   CLIENT_ID=<your-user-assigned-identity-client-id>
   ```

3. **Grant Fabric Access Permissions**:
   - Ensure the managed identity has appropriate access to the Microsoft Fabric workspace
   - Required permissions include:
     - Microsoft Fabric Item Reader role on the workspace
     - Microsoft Fabric Item User role on the Data Agent

### Static Web App Configuration

The Static Web App should be configured with the following:

1. **API Backend URL**:
   - Ensure the Static Web App is configured to communicate with your Function App
   - This is typically handled in the `staticwebapp.config.json` file

2. **CORS Settings**:
   - Ensure CORS is properly configured to allow communication between the Static Web App and Function App
   - The Function App is already configured to allow requests from Azure Static Web App domains

## Verification Steps

To verify the deployment is working correctly:

1. **Test API Health Endpoint**:

   ```http
   GET https://your-function-app.azurewebsites.net/health
   ```

   Should return a 200 OK response

2. **Test Authentication**:
   Try sending a simple request to the chat endpoint to verify authentication is working

3. **Monitor Application Insights**:
   - Check for any authentication failures or API errors
   - Look for 401/403 responses which may indicate permission issues

## Common Issues and Solutions

### Authentication Issues

- **401 Unauthorized**: Verify the managed identity is enabled and has correct permissions
- **403 Forbidden**: Check that the managed identity has been granted access to the Fabric workspace

### API Connection Issues

- **404 Not Found**: Verify the DATA_AGENT_URL is correct and the Data Agent is published
- **Timeout Errors**: The Data Agent may be in a cold start state; subsequent requests should be faster

### General Troubleshooting

- **Check Function App Logs**: Review the logs for detailed error messages
- **Verify Environment Variables**: Ensure all required environment variables are set correctly
- **Test Locally First**: Confirm functionality in local development before deploying

## Development vs. Production

The client is designed to automatically detect whether it's running in development or production:

- **In development**: Uses Azure CLI or interactive browser authentication
- **In production**: Uses Managed Identity authentication

This means you can develop locally without changing code when deploying to production.