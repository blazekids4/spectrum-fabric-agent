Fabric Agent Service — quick start

This repo includes a small FastAPI wrapper around the Fabric Data Agent client for multi-turn interactions.

1) Install dependencies (use virtualenv):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install fastapi uvicorn[standard] python-dotenv
```

2) Set environment variables (PowerShell):

```powershell
$Env:TENANT_ID = 'your-tenant-id'
$Env:DATA_AGENT_URL = 'https://<your-fabric-agent-endpoint>'
```

3) Start the service:

```powershell
uvicorn fabric_agent_service:app --host 127.0.0.1 --port 8001
```

4) Update frontend to point to service (in `.env.local` at frontend root):

```
NEXT_PUBLIC_FABRIC_AGENT_URL=http://127.0.0.1:8001/chat
```

5) Start the Next.js frontend (from `charter/frontend`):

```powershell
pnpm install
pnpm dev
```

Notes:
- Sessions are stored in-memory; consider Redis for production.
- The FabricDataAgentClient performs interactive auth; ensure the runtime has a browser available for authentication.
