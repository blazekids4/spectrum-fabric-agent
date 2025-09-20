# Charter VIP Backend - Local Deployment Guide

This guide walks you through deploying the Charter VIP backend system locally, including the Fabric Data Agent integration and multi-agent analysis system.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Azure Configuration](#azure-configuration)
- [Microsoft Fabric Setup](#microsoft-fabric-setup)
- [Local Installation](#local-installation)
- [Running the Services](#running-the-services)
- [Testing the Deployment](#testing-the-deployment)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Windows 10/11, macOS, or Linux
- **Python**: 3.8 or higher
- **Node.js**: 18+ (for frontend integration)
- **Memory**: At least 8GB RAM recommended
- **Storage**: 2GB free space

### Required Accounts

1. **Azure Account** with:

   - Azure AI Foundry access
   - Azure OpenAI service provisioned
   - Appropriate permissions to create service principals

2. **Microsoft Fabric Workspace** with:
   - Lakehouse created
   - Data Agent deployed
   - API access enabled

### Software Dependencies

```bash
# Check Python version
python --version  # Should be 3.8+

# Check pip
pip --version

# Install git (if not installed)
# Windows: Download from https://git-scm.com/
# macOS: brew install git
# Linux: sudo apt-get install git
```

## Environment Setup

### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/charter/charter-vip.git
cd charter-vip/backend

# Or if you already have it
cd c:\Users\justinlyons\source\repos\charter-vip\backend
```

### 2. Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install required packages
pip install -r requirements.txt

# If requirements.txt doesn't exist, create it:
cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0
httpx==0.25.2
azure-identity==1.15.0
azure-keyvault-secrets==4.7.0
openai==1.3.7
aiofiles==23.2.1
python-multipart==0.0.6
pandas==2.1.3
numpy==1.24.3
EOF

pip install -r requirements.txt
```

## Azure Configuration

### 1. Create Azure Resources

#### a. Azure OpenAI Service

```bash
# Using Azure CLI (install from https://aka.ms/installazurecli)
az login

# Create resource group
az group create --name charter-vip-rg --location eastus

# Create Azure OpenAI instance
az cognitiveservices account create \
  --name charter-vip-openai \
  --resource-group charter-vip-rg \
  --kind OpenAI \
  --sku S0 \
  --location eastus
```

#### b. Deploy Models

```bash
# Deploy GPT-4 model
az cognitiveservices account deployment create \
  --name charter-vip-openai \
  --resource-group charter-vip-rg \
  --deployment-name gpt-4o-mini \
  --model-name gpt-4 \
  --model-version "0613" \
  --model-format OpenAI
```

### 2. Get Azure Credentials

```bash
# Get your tenant ID
az account show --query tenantId -o tsv

# Get subscription ID
az account show --query id -o tsv

# Get OpenAI endpoint and key
az cognitiveservices account show \
  --name charter-vip-openai \
  --resource-group charter-vip-rg \
  --query properties.endpoint -o tsv

az cognitiveservices account keys list \
  --name charter-vip-openai \
  --resource-group charter-vip-rg \
  --query key1 -o tsv
```

## Microsoft Fabric Setup

### 1. Create Fabric Workspace

1. Navigate to [Microsoft Fabric](https://app.fabric.microsoft.com/)
2. Sign in with your organizational account
3. Create a new workspace named `charter-vip-workspace`

### 2. Create Lakehouse

1. In your workspace, click **+ New** → **Lakehouse**
2. Name it `charter_vip_lakehouse`
3. Note the workspace ID and lakehouse ID from the URL

### 3. Deploy Data Agent

1. In the lakehouse, go to **Settings** → **Data Agent**
2. Click **Create Data Agent**
3. Configure with:
   - Name: `charter-vip-data-agent`
   - Description: "Charter VIP Competitive Intelligence Data Agent"
   - Enable API access
4. Copy the Data Agent URL after creation

### 4. Upload Sample Data

Create a sample CSV file for testing:

```csv
# Create sample_transcripts.csv
call_id,transcript,date,customer_id,competitor_mentioned
1001,"Customer called asking about our internet plans. They mentioned AT&T has a promotion.",2024-01-15,C123,AT&T
1002,"Thinking of switching to Verizon because of their unlimited data offer.",2024-01-15,C124,Verizon
1003,"T-Mobile offered better coverage in my area. What can Charter do?",2024-01-16,C125,T-Mobile
```

Upload to lakehouse:

1. In lakehouse, go to **Files** section
2. Upload `sample_transcripts.csv`
3. Create a table from the file

## Local Installation

### 1. Create Environment Configuration

Create `.env` file in the backend directory:

```bash
# filepath: c:\Users\justinlyons\source\repos\charter-vip\backend\.env
# Azure Configuration
TENANT_ID=your-tenant-id-from-azure
SUBSCRIPTION_ID=your-subscription-id

# Fabric Configuration
FABRIC_WORKSPACE_ID=your-workspace-id-from-fabric
LAKEHOUSE_ID=your-lakehouse-id
DATA_AGENT_URL=https://your-data-agent-url.fabric.microsoft.com/

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_KEY=your-openai-key
MODEL_DEPLOYMENT_NAME=gpt-4o-mini

# Multi-Agent Configuration
PROJECT_ENDPOINT_MULTI_AGENT_CHARTER=https://your-ai-foundry.services.ai.azure.com/
MODEL_ROUTER_DEPLOYMENT=o1-multi-agent
MODEL_ROUTER_ENDPOINT=https://your-router.services.ai.azure.com/

# API Configuration
API_PORT=8001
API_HOST=127.0.0.1
FRONTEND_URL=http://localhost:3000

# Optional - Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxx

# Data Files (relative paths)
DATA_SOURCE_PATH=./data/source.csv
COMPETITOR_MAPPING_PATH=./data/competitor_normalization.json
```

### 2. Create Data Directory Structure

```bash
# Create necessary directories
mkdir -p data logs cache

# Create competitor normalization file
cat > data/competitor_normalization.json << 'EOF'
{
  "AT&T": ["att", "at&t", "at and t", "a t t", "att wireless", "at & t"],
  "Verizon": ["vzw", "verizon wireless", "vz", "verison", "verizon fios"],
  "T-Mobile": ["tmobile", "t mobile", "tmo", "t-mo", "t mo"],
  "Comcast": ["xfinity", "comcast cable", "xfin", "comcast business"],
  "Spectrum": ["charter spectrum", "spectrum internet", "spectrum cable"],
  "Cox": ["cox communications", "cox cable", "cox internet"],
  "Frontier": ["frontier communications", "frontier internet", "frontier fios"]
}
EOF
```

### 3. Create Test Data

```bash
# Create sample source data
cat > data/source.csv << 'EOF'
call_id,transcript,date,customer_id
1001,"I'm thinking of switching to AT&T because they have better prices",2024-01-15,C123
1002,"Verizon offered me unlimited data for $10 less than my current plan",2024-01-15,C124
1003,"The T-Mobile store said they have 5G in my area but Charter doesn't",2024-01-16,C125
1004,"My neighbor has Comcast and their internet seems faster",2024-01-16,C126
1005,"I'm happy with Charter service, just checking if you can match AT&T pricing",2024-01-17,C127
EOF
```

## Running the Services

### 1. Test Fabric Data Agent Connection

```bash
# Test the Fabric client directly
python -c "
from fabric_data_agent_client import FabricDataAgentClient
import os
from dotenv import load_dotenv

load_dotenv()

client = FabricDataAgentClient(
    tenant_id=os.getenv('TENANT_ID'),
    data_agent_url=os.getenv('DATA_AGENT_URL')
)

response = client.ask('What tables are available in the lakehouse?')
print(response)
"
```

### 2. Start the FastAPI Backend

```bash
# Make sure you're in the backend directory with activated venv
cd c:\Users\justinlyons\source\repos\charter-vip\backend

# Start the API server
python app.py

# Or use uvicorn directly with auto-reload for development
uvicorn app:app --host 127.0.0.1 --port 8001 --reload
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Starting Charter VIP Backend API...
INFO:     Fabric client initialized successfully
INFO:     Application startup complete.
```

### 3. Verify API is Running

Open a new terminal and test the endpoints:

```bash
# Check health
curl http://localhost:8001/

# Create a session
curl -X POST http://localhost:8001/session

# Test chat endpoint
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What competitors are mentioned most in recent calls?"}'

# Test Fabric query
curl -X POST http://localhost:8001/api/fabric/query \
  -H "Content-Type: application/json" \
  -d '"Show me the tables in the lakehouse"'
```

### 4. Run with Multiple Workers (Production-like)

```bash
# For production-like setup with multiple workers
uvicorn app:app --host 127.0.0.1 --port 8001 --workers 4
```

## Testing the Deployment

### 1. Interactive Testing Script

Create `test_local_deployment.py`:

```python
# filepath: c:\Users\justinlyons\source\repos\charter-vip\backend\test_local_deployment.py
import requests
import json
import time

BASE_URL = "http://localhost:8001"

def test_health():
    """Test API health endpoint"""
    response = requests.get(f"{BASE_URL}/")
    print("Health Check:", response.json())
    return response.status_code == 200

def test_session():
    """Test session creation"""
    response = requests.post(f"{BASE_URL}/session")
    session_data = response.json()
    print("Session Created:", session_data)
    return session_data.get("session_id")

def test_chat(session_id=None):
    """Test chat functionality"""
    queries = [
        "What competitors are mentioned in our call transcripts?",
        "Show me AT&T related calls from this week",
        "What are customers saying about Verizon's promotions?"
    ]

    for query in queries:
        print(f"\n📝 Query: {query}")
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"message": query, "session_id": session_id}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response: {data['reply'][:200]}...")
            if 'metadata' in data:
                print(f"📊 Metadata: {data['metadata']}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")

        time.sleep(2)  # Pause between requests

def test_fabric_direct():
    """Test direct Fabric queries"""
    response = requests.post(
        f"{BASE_URL}/api/fabric/query",
        json="SELECT COUNT(*) as total_calls FROM call_transcripts"
    )

    print("\nDirect Fabric Query Result:")
    print(response.json())

def test_competitor_analysis():
    """Test competitor analysis endpoint"""
    response = requests.post(
        f"{BASE_URL}/api/multi-agent/competitor/AT&T",
        json={
            "competitor_name": "AT&T",
            "date_range": {"start": "2024-01-01", "end": "2024-01-31"},
            "include_promotions": True,
            "include_sentiment": True,
            "include_switching": True
        }
    )

    print("\nCompetitor Analysis for AT&T:")
    print(json.dumps(response.json(), indent=2))

def main():
    print("🚀 Testing Charter VIP Local Deployment\n")

    # Test health
    if not test_health():
        print("❌ API is not running! Please start it first.")
        return

    # Test session management
    session_id = test_session()

    # Test chat with context
    test_chat(session_id)

    # Test Fabric integration
    test_fabric_direct()

    # Test multi-agent analysis
    test_competitor_analysis()

    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
```

Run the test script:

```bash
python test_local_deployment.py
```

### 2. Frontend Integration Test

If you have the frontend running:

```bash
# In a new terminal, navigate to frontend
cd ../frontend

# Install dependencies
npm install

# Update .env.local to point to local backend
echo "NEXT_PUBLIC_API_URL=http://localhost:8001" > .env.local

# Start frontend
npm run dev
```

Navigate to http://localhost:3000 and test the chat interface.

## Troubleshooting

### Common Issues and Solutions

#### 1. Authentication Issues

```bash
# Error: "Authentication failed"
# Solution: Clear Azure CLI cache and re-authenticate
az account clear
az login --tenant your-tenant-id
```

#### 2. Fabric Connection Issues

```bash
# Error: "Failed to connect to Data Agent"
# Solution: Verify Data Agent URL and ensure it's accessible
curl -X GET "your-data-agent-url" -H "Authorization: Bearer $(az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv)"
```

#### 3. Import Errors

```bash
# Error: "ModuleNotFoundError"
# Solution: Ensure you're in the virtual environment
which python  # Should show venv path
pip list  # Verify packages are installed
```

#### 4. Port Already in Use

```bash
# Error: "Address already in use"
# Solution: Find and kill the process
# Windows:
netstat -ano | findstr :8001
taskkill /PID <PID> /F

# macOS/Linux:
lsof -i :8001
kill -9 <PID>
```

#### 5. Memory Issues

```python
# Add to app.py for memory optimization
import gc

# After heavy operations
gc.collect()
```

### Debug Mode

Run with enhanced logging:

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Run with debug logging
uvicorn app:app --host 127.0.0.1 --port 8001 --log-level debug
```

### Performance Monitoring

Create `monitor.py` for local performance monitoring:

```python
import psutil
import time

def monitor_app():
    process = psutil.Process()
    while True:
        cpu = process.cpu_percent(interval=1)
        memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"CPU: {cpu}% | Memory: {memory:.2f} MB")
        time.sleep(5)

if __name__ == "__main__":
    monitor_app()
```

## Next Steps

1. **Configure Multi-Agent System**: Set up the `fabric_data_agent_multi_agent.py` with your specific analysis requirements

2. **Add Custom Endpoints**: Extend `app.py` with business-specific endpoints

3. **Set Up Monitoring**: Integrate Application Insights for production monitoring

4. **Implement Caching**: Add Redis for production-grade caching

5. **Security Hardening**:
   - Add API key authentication
   - Implement rate limiting
   - Set up HTTPS for local development

## Support

If you encounter issues:

1. Check the logs in the `logs/` directory
2. Verify all environment variables are set correctly
3. Ensure all Azure resources are properly provisioned
4. Review the Fabric Data Agent documentation

For additional help:

- Internal Wiki: `https://wiki.charter.com/charter-vip`
- Team Channel: `#charter-vip-support`
- Email: `charter-vip-dev@charter.com`

---

**Happy Deploying! 🚀**
