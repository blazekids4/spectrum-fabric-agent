#!/usr/bin/env python3
"""
Main FastAPI application entry point for Charter VIP backend.
Orchestrates both the Fabric Data Agent Client and Multi-Agent Analysis system.

This serves as the primary API layer between the Next.js frontend 
and the Fabric Data Agent backend services.
"""
import os
import sys
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import logging
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager
import json


# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our primary modules
from fabric_data_agent_client import FabricDataAgentClient
# Import the multi-agent system (assuming it exports necessary functions)
# You'll need to ensure fabric_data_agent_multi_agent.py exports these functions
try:
    from fabric_data_agent_multi_agent import (
        run_competitor_analysis,
        process_call_transcripts,
        generate_competitive_insights,
        normalize_competitor_names
    )
except ImportError:
    # Define placeholder functions if imports fail
    async def run_competitor_analysis(*args, **kwargs):
        return {"error": "Multi-agent system not available"}
    
    async def process_call_transcripts(*args, **kwargs):
        return {"error": "Transcript processing not available"}
    
    async def generate_competitive_insights(*args, **kwargs):
        return {"error": "Insight generation not available"}
    
    def normalize_competitor_names(text):
        return text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for service management
fabric_client: Optional[FabricDataAgentClient] = None
multi_agent_executor = None
client_lock = asyncio.Lock()
analysis_cache: Dict[str, Any] = {}
sessions: Dict[str, Dict[str, Any]] = {}

# Cache configuration
CACHE_TTL = 3600  # 1 hour in seconds
ANALYSIS_CACHE_TTL = 86400  # 24 hours for analysis results

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle - startup and shutdown events.
    """
    # Startup
    logger.info("Starting Charter VIP Backend API...")
    
    # Initialize services if credentials are available
    if os.getenv("TENANT_ID") and os.getenv("DATA_AGENT_URL"):
        try:
            await ensure_fabric_client()
            logger.info("Fabric client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Fabric client at startup: {e}")
    
    # Initialize multi-agent system if available
    try:
        await initialize_multi_agent_system()
        logger.info("Multi-agent system initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize multi-agent system: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Charter VIP Backend API...")
    # Cleanup resources
    await cleanup_resources()

# Create FastAPI app with lifespan manager
app = FastAPI(
    title="Charter VIP Backend API",
    description="Backend services for Charter VIP competitive intelligence and customer service",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS for Vercel deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://*.vercel.app",   # Vercel preview deployments
        os.getenv("FRONTEND_URL", "https://charter-vip.vercel.app")  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    context: Optional[Dict[str, Any]] = {}

class ChatResponse(BaseModel):
    session_id: str
    reply: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    sources: Optional[List[str]] = []

class TranscriptAnalysisRequest(BaseModel):
    transcript_batch: Optional[List[Dict[str, str]]] = None  # List of {call_id, transcript, date}
    source_file: Optional[str] = None  # Or path to CSV file
    analysis_type: str = "full"  # "full", "competitors_only", "sentiment_only"

class CompetitorAnalysisRequest(BaseModel):
    competitor_name: str
    date_range: Optional[Dict[str, str]] = {"start": None, "end": None}
    include_promotions: bool = True
    include_sentiment: bool = True
    include_switching: bool = True

class MultiAgentQueryRequest(BaseModel):
    query: str
    agents: Optional[List[str]] = ["fabric", "web_search", "table_analysis"]
    max_iterations: int = 3
    include_raw_data: bool = False

# Helper functions
async def ensure_fabric_client():
    """Ensure Fabric client is initialized."""
    global fabric_client
    if fabric_client is not None:
        return fabric_client
    
    async with client_lock:
        if fabric_client is None:
            tenant_id = os.getenv("TENANT_ID")
            data_agent_url = os.getenv("DATA_AGENT_URL")
            
            if not tenant_id or not data_agent_url:
                raise HTTPException(
                    status_code=500, 
                    detail="Fabric client not configured. Set TENANT_ID and DATA_AGENT_URL env vars."
                )
            
            fabric_client = FabricDataAgentClient(
                tenant_id=tenant_id, 
                data_agent_url=data_agent_url
            )
    
    return fabric_client

async def initialize_multi_agent_system():
    """Initialize the multi-agent analysis system."""
    global multi_agent_executor
    # Initialize your multi-agent system here
    # This depends on how fabric_data_agent_multi_agent.py is structured
    logger.info("Multi-agent system initialization placeholder")

async def cleanup_resources():
    """Clean up resources on shutdown."""
    global fabric_client, multi_agent_executor
    # Add cleanup logic here
    fabric_client = None
    multi_agent_executor = None

def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Get existing session or create new one."""
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {},
            "analysis_results": {}
        }
    
    return session_id

def get_cache_key(prefix: str, params: Dict[str, Any]) -> str:
    """Generate cache key from parameters."""
    param_str = json.dumps(params, sort_keys=True)
    return f"{prefix}:{hash(param_str)}"

def is_cache_valid(cache_entry: Dict[str, Any], ttl: int = CACHE_TTL) -> bool:
    """Check if cache entry is still valid."""
    if not cache_entry:
        return False
    
    cached_time = cache_entry.get("timestamp", datetime.min)
    if isinstance(cached_time, str):
        cached_time = datetime.fromisoformat(cached_time)
    
    return (datetime.utcnow() - cached_time).total_seconds() < ttl

# API Routes

@app.get("/")
async def root():
    """Health check and API info."""
    return {
        "status": "healthy",
        "service": "Charter VIP Backend API",
        "version": "2.0.0",
        "capabilities": {
            "fabric_data_agent": fabric_client is not None,
            "multi_agent_analysis": multi_agent_executor is not None
        },
        "endpoints": {
            "chat": "/chat",
            "fabric_agent": {
                "direct_query": "/api/fabric/query",
                "detailed_analysis": "/api/fabric/analyze"
            },
            "multi_agent": {
                "run_analysis": "/api/multi-agent/analyze",
                "competitor_analysis": "/api/multi-agent/competitor/{name}",
                "transcript_processing": "/api/multi-agent/transcripts"
            },
            "insights": {
                "summary": "/api/insights/summary",
                "competitors": "/api/insights/competitors/{name}",
                "trends": "/api/trends/weekly",
                "promotions": "/api/promotions/active"
            }
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint that intelligently routes to appropriate backend service.
    Uses Fabric Data Agent for data queries and Multi-Agent for complex analysis.
    """
    try:
        session_id = get_or_create_session(request.session_id)
        
        # Add user message to history
        sessions[session_id]["history"].append({
            "role": "user",
            "text": request.message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Determine which backend to use based on query
        query_lower = request.message.lower()
        
        # Route to multi-agent for competitor analysis
        if any(keyword in query_lower for keyword in ["competitor", "at&t", "verizon", "t-mobile", "comcast", "promotion", "switch"]):
            # Use multi-agent system for competitive intelligence
            response = await handle_multi_agent_query(request.message, session_id)
        else:
            # Use Fabric Data Agent for general data queries
            response = await handle_fabric_query(request.message, session_id)
        
        # Add response to history
        sessions[session_id]["history"].append({
            "role": "assistant",
            "text": response["reply"],
            "timestamp": datetime.utcnow().isoformat(),
            "sources": response.get("sources", [])
        })
        
        return ChatResponse(
            session_id=session_id,
            reply=response["reply"],
            metadata=response.get("metadata", {}),
            sources=response.get("sources", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_fabric_query(query: str, session_id: str) -> Dict[str, Any]:
    """Handle query using Fabric Data Agent."""
    fabric_client = await ensure_fabric_client()
    
    # Build context from session history
    history_context = "\n".join([
        f"{msg['role']}: {msg['text']}" 
        for msg in sessions[session_id]["history"][-5:]  # Last 5 messages
    ])
    
    prompt = f"""You are Charter's AI assistant with access to the company's data lakehouse.
    
Previous conversation:
{history_context}

Current question: {query}

Please provide a helpful, accurate response based on the data available."""
    
    # Get response from Fabric agent
    reply = fabric_client.ask(prompt)
    
    # For detailed queries, also get run details
    if "sql" in query.lower() or "query" in query.lower():
        details = fabric_client.get_run_details(query)
        if "sql_queries" in details:
            return {
                "reply": reply,
                "metadata": {
                    "sql_queries": details.get("sql_queries", []),
                    "data_preview": details.get("sql_data_previews", [])
                },
                "sources": ["Fabric Lakehouse"]
            }
    
    return {
        "reply": reply,
        "sources": ["Fabric Data Agent"]
    }

async def handle_multi_agent_query(query: str, session_id: str) -> Dict[str, Any]:
    """Handle query using Multi-Agent system."""
    try:
        # Normalize competitor names in the query
        normalized_query = normalize_competitor_names(query)
        
        # Run multi-agent analysis
        result = await run_competitor_analysis(
            query=normalized_query,
            session_context=sessions[session_id]["history"]
        )
        
        if isinstance(result, dict) and "error" in result:
            # Fallback to Fabric agent if multi-agent unavailable
            return await handle_fabric_query(query, session_id)
        
        return {
            "reply": result.get("summary", "Analysis completed"),
            "metadata": {
                "analysis_type": "multi_agent",
                "agents_used": result.get("agents_used", []),
                "insights": result.get("insights", {})
            },
            "sources": result.get("sources", ["Multi-Agent Analysis"])
        }
        
    except Exception as e:
        logger.error(f"Multi-agent query error: {str(e)}")
        # Fallback to Fabric agent
        return await handle_fabric_query(query, session_id)

# Fabric Data Agent specific endpoints
@app.post("/api/fabric/query")
async def fabric_direct_query(query: str):
    """Direct query to Fabric Data Agent."""
    try:
        fabric_client = await ensure_fabric_client()
        response = fabric_client.ask(query)
        return {
            "query": query,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Fabric query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/fabric/analyze")
async def fabric_detailed_analysis(query: str):
    """Get detailed analysis including SQL queries and data preview."""
    try:
        fabric_client = await ensure_fabric_client()
        details = fabric_client.get_run_details(query)
        return {
            "query": query,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Fabric analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Multi-Agent specific endpoints
@app.post("/api/multi-agent/analyze")
async def multi_agent_analysis(request: MultiAgentQueryRequest):
    """Run multi-agent analysis with specified agents."""
    try:
        result = await generate_competitive_insights(
            query=request.query,
            agents=request.agents,
            max_iterations=request.max_iterations
        )
        
        return {
            "query": request.query,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Multi-agent analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/multi-agent/competitor/{competitor_name}")
async def analyze_competitor(competitor_name: str, request: CompetitorAnalysisRequest):
    """Deep dive analysis on specific competitor."""
    try:
        # Check cache first
        cache_key = get_cache_key("competitor", {"name": competitor_name, **request.dict()})
        if cache_key in analysis_cache and is_cache_valid(analysis_cache[cache_key], ANALYSIS_CACHE_TTL):
            return analysis_cache[cache_key]["data"]
        
        # Run analysis
        result = await run_competitor_analysis(
            competitor=competitor_name,
            date_range=request.date_range,
            include_promotions=request.include_promotions,
            include_sentiment=request.include_sentiment,
            include_switching=request.include_switching
        )
        
        # Cache result
        response_data = {
            "competitor": competitor_name,
            "analysis": result,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        analysis_cache[cache_key] = {
            "data": response_data,
            "timestamp": datetime.utcnow()
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Competitor analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/multi-agent/transcripts")
async def process_transcripts(request: TranscriptAnalysisRequest, background_tasks: BackgroundTasks):
    """Process call transcripts for competitive insights."""
    try:
        job_id = str(uuid.uuid4())
        
        # Start processing in background
        background_tasks.add_task(
            process_transcripts_background,
            job_id,
            request.transcript_batch,
            request.source_file,
            request.analysis_type
        )
        
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Transcript processing started"
        }
        
    except Exception as e:
        logger.error(f"Transcript processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_transcripts_background(job_id: str, transcript_batch, source_file, analysis_type):
    """Background task for processing transcripts."""
    try:
        result = await process_call_transcripts(
            transcript_batch=transcript_batch,
            source_file=source_file,
            analysis_type=analysis_type
        )
        
        analysis_cache[job_id] = {
            "status": "completed",
            "result": result,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Background transcript processing error: {str(e)}")
        analysis_cache[job_id] = {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }

# Combined insights endpoints (use both Fabric and Multi-Agent)
@app.get("/api/insights/summary")
async def get_executive_summary():
    """
    Get executive summary combining Fabric data and multi-agent analysis.
    """
    try:
        # Check cache
        cache_key = "executive_summary"
        if cache_key in analysis_cache and is_cache_valid(analysis_cache[cache_key]):
            return analysis_cache[cache_key]["data"]
        
        # Get data from both sources
        fabric_client = await ensure_fabric_client()
        
        # Fabric query for data summary
        fabric_summary = fabric_client.ask(
            "Provide a summary of key metrics and trends from the last 7 days"
        )
        
        # Multi-agent competitive analysis
        competitive_summary = await generate_competitive_insights(
            query="Summarize competitive landscape and key competitor activities from the last week",
            agents=["fabric", "web_search", "table_analysis"]
        )
        
        # Combine insights
        combined_summary = {
            "data_insights": fabric_summary,
            "competitive_insights": competitive_summary,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Cache result
        analysis_cache[cache_key] = {
            "data": combined_summary,
            "timestamp": datetime.utcnow()
        }
        
        return combined_summary
        
    except Exception as e:
        logger.error(f"Summary generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/job/{job_id}/status")
async def get_job_status(job_id: str):
    """Check status of background processing job."""
    if job_id in analysis_cache:
        return analysis_cache[job_id]
    else:
        raise HTTPException(status_code=404, detail="Job not found")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# For Vercel deployment
handler = app

# Development server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5328)