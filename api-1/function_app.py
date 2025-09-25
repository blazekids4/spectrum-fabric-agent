
import azure.functions as func
import logging
import os
import sys
from fastapi import FastAPI
from azure.functions import AsgiRequest, AsgiResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
logger.info("Starting Azure Function app...")
logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")

# Log environment variables (redact sensitive information)
logger.info("Environment variables check:")
for key in ['TENANT_ID', 'DATA_AGENT_URL', 'WEBSITES_PORT']:
    if key in os.environ:
        if key in ['TENANT_ID', 'DATA_AGENT_URL']:
            logger.info(f"{key}: [REDACTED - PRESENT]")
        else:
            logger.info(f"{key}: {os.environ.get(key)}")
    else:
        logger.warning(f"{key}: NOT SET")

# Import your existing app
try:
    from app import app as fastapi_app
    logger.info("Successfully imported FastAPI app from app.py")
except Exception as e:
    logger.error(f"Error importing FastAPI app: {str(e)}")
    raise

# Create function app
app = func.FunctionApp()

@app.function_name(name="HttpTrigger")
@app.route(route="{*route}", methods=["GET", "POST", "PUT", "DELETE"])
async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Process all HTTP requests through FastAPI"""
    try:
        # Log incoming request
        logger.info(f"Received {req.method} request to {req.url}")
        
        # Convert Azure Function request to ASGI
        asgi_request = AsgiRequest(req)
        asgi_response = await fastapi_app(
            asgi_request.receive,
            asgi_request.send
        )
        
        # Log response status
        logger.info(f"Responding with status code {asgi_response.status_code}")
        
        return func.HttpResponse(
            body=asgi_response.body,
            status_code=asgi_response.status_code,
            headers=dict(asgi_response.headers)
        )
    except Exception as e:
        # Log any exceptions
        logger.error(f"Error processing request: {str(e)}")
        
        # Return error response
        return func.HttpResponse(
            body=str(e),
            status_code=500,
            headers={"Content-Type": "text/plain"}
        )