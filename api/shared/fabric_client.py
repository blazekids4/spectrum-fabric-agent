"""
Microsoft Fabric Data Agent client using Azure Managed Identity.
Handles authentication and communication with Fabric Data Agent services.
"""
import os
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from fabric.dataagent.client import FabricOpenAI
import sempy.fabric as fabric

logger = logging.getLogger(__name__)

class FabricClient:
    """Client for interacting with Microsoft Fabric Data Agent using managed identity."""
    
    def __init__(self):
        """Initialize Fabric client with managed identity credentials."""
        self.data_agent_name = os.getenv("FABRIC_DATA_AGENT_NAME")
        self.workspace_id = os.getenv("FABRIC_WORKSPACE_ID")
        self.model_name = os.getenv("FABRIC_MODEL_NAME", "gpt-4o")
        
        if not self.data_agent_name:
            raise ValueError("FABRIC_DATA_AGENT_NAME environment variable is required")
        
        # Initialize Azure credentials for Fabric authentication
        if os.getenv("AZURE_CLIENT_ID"):
            # Production with managed identity
            self.credential = ManagedIdentityCredential(
                client_id=os.getenv("AZURE_CLIENT_ID")
            )
        else:
            # Local development with Azure CLI or other auth methods
            self.credential = DefaultAzureCredential()
        
        # Initialize Fabric client with authentication
        self._initialize_fabric_auth()
        
        # Initialize the FabricOpenAI client
        self.fabric_client = None
        self._initialize_fabric_client()
        
        logger.info(f"FabricClient initialized with Data Agent: {self.data_agent_name}")
    
    def _initialize_fabric_auth(self):
        """Initialize Fabric authentication using Azure credentials."""
        try:
            # Set up Fabric authentication context
            # This may vary based on your specific Fabric setup
            token = self.credential.get_token("https://analysis.windows.net/powerbi/api/.default")
            
            # Configure sempy/fabric authentication if needed
            # This depends on how your environment is configured
            if hasattr(fabric, 'set_auth_token'):
                fabric.set_auth_token(token.token)
                
        except Exception as e:
            logger.error(f"Failed to initialize Fabric authentication: {e}")
            raise
    
    def _initialize_fabric_client(self):
        """Initialize the Fabric OpenAI client."""
        try:
            self.fabric_client = FabricOpenAI(
                artifact_name=self.data_agent_name,
                workspace_id=self.workspace_id  # If supported by the SDK
            )
        except Exception as e:
            logger.error(f"Failed to initialize Fabric OpenAI client: {e}")
            raise
    
    async def process_chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Process chat messages through Microsoft Fabric Data Agent.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            Response from Fabric Data Agent
        """
        try:
            # Extract the user's question from messages
            user_message = None
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    user_message = msg.get('content')
                    break
            
            if not user_message:
                return {
                    "success": False,
                    "error": "No user message found in request"
                }
            
            # Run the query synchronously in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                self._query_fabric_sync, 
                user_message
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing chat: {e}")
            return {
                "success": False,
                "error": "Failed to process chat request",
                "details": str(e)
            }
    
    def _query_fabric_sync(self, question: str) -> Dict[str, Any]:
        """
        Synchronous method to query Fabric Data Agent.
        
        Args:
            question: The user's question
            
        Returns:
            Response dictionary
        """
        assistant = None
        thread = None
        
        try:
            # Create assistant and thread
            assistant = self.fabric_client.beta.assistants.create(model=self.model_name)
            thread = self.fabric_client.beta.threads.create()
            
            logger.info(f"Created assistant: {assistant.id}, thread: {thread.id}")
            
            # Create a message with the question
            self.fabric_client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=question
            )
            
            # Create and run the query
            run = self.fabric_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            logger.info(f"Created run: {run.id}")
            
            # Wait for completion with timeout
            max_wait_time = 60  # seconds
            start_time = time.time()
            
            while run.status in ["queued", "in_progress"]:
                if time.time() - start_time > max_wait_time:
                    raise TimeoutError("Query timed out after 60 seconds")
                
                run = self.fabric_client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                time.sleep(2)
            
            # Check if run completed successfully
            if run.status != "completed":
                raise Exception(f"Run failed with status: {run.status}")
            
            # Retrieve the response
            messages_response = self.fabric_client.beta.threads.messages.list(
                thread_id=thread.id,
                order="asc"
            )
            
            # Extract assistant's response
            assistant_response = self._extract_assistant_response(messages_response.data)
            
            return {
                "success": True,
                "message": assistant_response,
                "metadata": {
                    "run_id": run.id,
                    "thread_id": thread.id,
                    "status": run.status
                }
            }
            
        except Exception as e:
            logger.error(f"Error in Fabric query: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Clean up thread
            if thread:
                try:               
                    self.fabric_client.beta.threads.delete(thread.id)
                except Exception as e:
                    logger.warning(f"Failed to delete thread: {e}")
    
    def _extract_assistant_response(self, messages: List[Any]) -> str:
        """
        Extract the assistant's response from messages.
        
        Args:
            messages: List of message objects
            
        Returns:
            The assistant's response text
        """
        assistant_messages = [m for m in messages if m.role == "assistant"]
        if assistant_messages:
            # Get the last assistant message
            last_message = assistant_messages[-1]
            if hasattr(last_message, 'content') and last_message.content:
                return last_message.content[0].text.value
        return "No response from assistant"
    
    async def close(self):
        """Close any open resources."""
        # The Fabric client doesn't seem to have async resources to close
        pass