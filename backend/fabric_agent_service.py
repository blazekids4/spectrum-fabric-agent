#!/usr/bin/env python3
"""
FastAPI service to provide a multi-turn interface to the Fabric Data Agent.

Endpoints:
- POST /chat    -> { session_id?, message } returns { session_id, reply }
- POST /session -> { } creates a new session id
- GET  /session/{session_id} -> returns session metadata

Sessions are stored in-memory (dict). For production, back this with Redis or DB.

Usage:
  pip install fastapi uvicorn[standard] python-dotenv
  export TENANT_ID=... DATA_AGENT_URL=...
  uvicorn fabric_agent_service:app --host 127.0.0.1 --port 8001

The service will initialize the FabricDataAgentClient lazily on first request.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import os
import asyncio
from fabric_data_agent_client import FabricDataAgentClient

app = FastAPI(title="Fabric Agent Service")

TENANT_ID = os.getenv("TENANT_ID", "your-tenant-id-here")
DATA_AGENT_URL = os.getenv("DATA_AGENT_URL", "your-data-agent-url-here")

# Simple in-memory session store: { session_id: { history: [ {role, text} ], created_at } }
SESSIONS: Dict[str, Dict[str, Any]] = {}

client: Optional[FabricDataAgentClient] = None
client_lock = asyncio.Lock()

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    global client
    # Lazy init - don't authenticate at startup if config missing
    if TENANT_ID != "your-tenant-id-here" and DATA_AGENT_URL != "your-data-agent-url-here":
        try:
            client = FabricDataAgentClient(tenant_id=TENANT_ID, data_agent_url=DATA_AGENT_URL)
        except Exception as e:
            # Keep client None and allow interactive init on first request
            client = None


@app.post("/session")
async def create_session():
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {"history": [], "created_at": __import__("time").time()}
    return {"session_id": session_id}


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="session not found")
    return {"session_id": session_id, "info": SESSIONS[session_id]}


async def ensure_client():
    global client
    if client is not None:
        return client
    async with client_lock:
        if client is None:
            if TENANT_ID == "your-tenant-id-here" or DATA_AGENT_URL == "your-data-agent-url-here":
                raise HTTPException(status_code=500, detail="Fabric client not configured. Set TENANT_ID and DATA_AGENT_URL env vars.")
            client = FabricDataAgentClient(tenant_id=TENANT_ID, data_agent_url=DATA_AGENT_URL)
    return client


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Ensure session
    session_id = req.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = {"history": [], "created_at": __import__("time").time()}

    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="session not found")

    # Append user message to session history
    SESSIONS[session_id]["history"].append({"role": "user", "text": req.message})

    # Build a prompt for the Fabric agent using session history
    history_text = "\n".join([f"{h['role']}: {h['text']}" for h in SESSIONS[session_id]["history"]])
    prompt = f"You are a Fabric Data Agent helper. Continue the conversation based on the following dialog and answer the user's last question.\n\n{history_text}\n\nAssistant:"  # Let agent produce a helpful reply

    # Ask the Fabric agent (or return dry-run placeholder if client not configured)
    try:
        fa_client = await ensure_client()
        reply = fa_client.ask(prompt)
    except HTTPException:
        # Bubble up
        raise
    except Exception as e:
        # If the client failed, save the error as reply
        reply = f"ERROR: {e}"

    # Append assistant reply
    SESSIONS[session_id]["history"].append({"role": "assistant", "text": reply})

    return {"session_id": session_id, "reply": reply}
