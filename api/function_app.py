"""
Azure Functions backend for Spectrum Fabric Agent.
Uses managed identity for secure Microsoft Fabric access.
"""
import logging
import json
import os
import uuid
from datetime import datetime
import azure.functions as func
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our shared modules
try:
    from shared.fabric_client import FabricClient
except ImportError:
    logger.error("Failed to import FabricClient. Ensure shared module is properly deployed.")
    FabricClient = None

# Create Function App instance
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Initialize Fabric client as a global to reuse connections
fabric_client = None

# In-memory session storage for development (use Redis or Cosmos DB in production)
sessions = {}

def get_fabric_client():
    """Get or create Fabric client instance."""
    global fabric_client
    if fabric_client is None and FabricClient:
        try:
            fabric_client = FabricClient()
        except Exception as e:
            logger.error(f"Failed to initialize Fabric client: {e}")
            fabric_client = None
    return fabric_client

def get_or_create_session(session_id: Optional[str], client_id: Optional[str]) -> str:
    """Get existing session or create a new one."""
    if session_id and session_id in sessions:
        return session_id
    
    # Create new session
    new_session_id = f"session-{uuid.uuid4()}"
    sessions[new_session_id] = {
        "id": new_session_id,
        "client_id": client_id,
        "created": datetime.utcnow().isoformat(),
        "messages": []
    }
    return new_session_id

@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for monitoring."""
    try:
        # Check if Fabric client can be initialized
        client = get_fabric_client()
        fabric_status = "connected" if client else "disconnected"
        
        return func.HttpResponse(
            json.dumps({
                "status": "healthy",
                "service": "spectrum-fabric-api",
                "version": "1.0.0",
                "fabric_status": fabric_status,
                "data_agent": os.getenv("FABRIC_DATA_AGENT_NAME", "not_configured"),
                "timestamp": datetime.utcnow().isoformat()
            }),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return func.HttpResponse(
            json.dumps({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }),
            mimetype="application/json",
            status_code=503
        )

@app.route(route="chat", methods=["POST", "OPTIONS"])
async def chat(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main chat endpoint that processes requests through Fabric Data Agent.
    Expects JSON body with 'messages' array and optional session_id, clientId, context.
    """
    # Handle CORS preflight
    if req.method == "OPTIONS":
        return func.HttpResponse(
            "",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, X-Client-Id"
            }
        )
    
    logger.info("Chat endpoint called")
    
    try:
        # Parse request body
        try:
            req_body = req.get_json()
        except ValueError:
            logger.error("Invalid JSON in request body")
            return func.HttpResponse(
                json.dumps({
                    "error": "Invalid JSON in request body",
                    "detail": "Request body must be valid JSON"
                }),
                mimetype="application/json",
                status_code=400,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Extract parameters
        messages = req_body.get('messages', [])
        session_id = req_body.get('session_id')
        client_id = req_body.get('clientId') or req.headers.get('X-Client-Id')
        context = req_body.get('context', {})
        
        # Validate request
        if not messages:
            logger.error("Missing or empty 'messages' in request body")
            return func.HttpResponse(
                json.dumps({
                    "error": "Missing or empty 'messages' in request body",
                    "detail": "At least one message is required"
                }),
                mimetype="application/json",
                status_code=400,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Get or create session
        session_id = get_or_create_session(session_id, client_id)
        
        # Store messages in session (for context in future requests)
        if session_id in sessions:
            sessions[session_id]["messages"].extend(messages)
            # Keep only last 10 messages to prevent memory issues
            sessions[session_id]["messages"] = sessions[session_id]["messages"][-10:]
        
        # Get Fabric client
        client = get_fabric_client()
        if not client:
            logger.error("Fabric client not available")
            return func.HttpResponse(
                json.dumps({
                    "error": "Service temporarily unavailable",
                    "detail": "Fabric client is not initialized"
                }),
                mimetype="application/json",
                status_code=503,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Add context to messages if provided
        if context:
            messages = [{
                **msg,
                "context": context
            } for msg in messages]
        
        # Process chat request through Fabric Data Agent
        logger.info(f"Processing chat for session {session_id} with {len(messages)} messages")
        response = await client.process_chat(messages)
        
        # Build response
        if response.get("success"):
            return func.HttpResponse(
                json.dumps({
                    "response": response.get("message", ""),
                    "session_id": session_id,
                    "metadata": {
                        **response.get("metadata", {}),
                        "session_id": session_id,
                        "client_id": client_id
                    }
                }),
                mimetype="application/json",
                status_code=200,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        else:
            return func.HttpResponse(
                json.dumps({
                    "error": response.get("error", "Unknown error"),
                    "detail": response.get("details"),
                    "session_id": session_id
                }),
                mimetype="application/json",
                status_code=500,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": "An error occurred processing your request",
                "detail": str(e) if os.getenv("ENVIRONMENT") == "development" else "Internal server error",
                "session_id": session_id if 'session_id' in locals() else None
            }),
            mimetype="application/json",
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )

@app.route(route="config", methods=["GET"])
def get_config(req: func.HttpRequest) -> func.HttpResponse:
    """Get current configuration (non-sensitive values only)."""
    config = {
        "environment": os.getenv("ENVIRONMENT", "production"),
        "version": "1.0.0",
        "managed_identity_enabled": os.getenv("AZURE_CLIENT_ID") is not None,
        "data_agent_configured": os.getenv("FABRIC_DATA_AGENT_NAME") is not None,
        "workspace_configured": os.getenv("FABRIC_WORKSPACE_ID") is not None,
        "model": os.getenv("FABRIC_MODEL_NAME", "gpt-4o"),
        "features": {
            "sessionManagement": True,
            "contextAware": True,
            "multiTurn": True
        }
    }
    
    return func.HttpResponse(
        json.dumps(config),
        mimetype="application/json",
        status_code=200,
        headers={"Access-Control-Allow-Origin": "*"}
    )

@app.route(route="query", methods=["POST"])
async def simple_query(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simplified endpoint for single question queries.
    Expects JSON body with 'question' field.
    """
    try:
        req_body = req.get_json()
        question = req_body.get('question')
        session_id = req_body.get('session_id')
        client_id = req_body.get('clientId')
        
        if not question:
            return func.HttpResponse(
                json.dumps({
                    "error": "Missing 'question' in request body",
                    "detail": "A question is required"
                }),
                mimetype="application/json",
                status_code=400,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Convert to messages format and process
        messages = [{"role": "user", "content": question}]
        
        # Get or create session
        session_id = get_or_create_session(session_id, client_id)
        
        # Process through chat endpoint logic
        client = get_fabric_client()
        if not client:
            return func.HttpResponse(
                json.dumps({
                    "error": "Service temporarily unavailable",
                    "detail": "Fabric client is not initialized"
                }),
                mimetype="application/json",
                status_code=503,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        response = await client.process_chat(messages)
        
        if response.get("success"):
            return func.HttpResponse(
                json.dumps({
                    "response": response.get("message", ""),
                    "session_id": session_id,
                    "metadata": response.get("metadata", {})
                }),
                mimetype="application/json",
                status_code=200,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        else:
            return func.HttpResponse(
                json.dumps({
                    "error": response.get("error", "Failed to get answer"),
                    "detail": response.get("details"),
                    "session_id": session_id
                }),
                mimetype="application/json",
                status_code=500,
                headers={"Access-Control-Allow-Origin": "*"}
            )
            
    except Exception as e:
        logger.error(f"Error in simple query: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": "Failed to process query",
                "detail": str(e) if os.getenv("ENVIRONMENT") == "development" else "Internal server error"
            }),
            mimetype="application/json",
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )

@app.route(route="sessions/{session_id}", methods=["GET", "DELETE"])
async def manage_session(req: func.HttpRequest) -> func.HttpResponse:
    """Get or delete a session."""
    session_id = req.route_params.get('session_id')
    
    if req.method == "GET":
        if session_id in sessions:
            return func.HttpResponse(
                json.dumps(sessions[session_id]),
                mimetype="application/json",
                status_code=200,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": "Session not found"}),
                mimetype="application/json",
                status_code=404,
                headers={"Access-Control-Allow-Origin": "*"}
            )
    
    elif req.method == "DELETE":
        if session_id in sessions:
            del sessions[session_id]
            return func.HttpResponse(
                json.dumps({"message": "Session deleted"}),
                mimetype="application/json",
                status_code=200,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": "Session not found"}),
                mimetype="application/json",
                status_code=404,
                headers={"Access-Control-Allow-Origin": "*"}
            )