import time
import uuid
import json
import os
import warnings
import logging
import typing as t
from typing import Optional, Dict, Any, List
from azure.identity import (
    ManagedIdentityCredential, 
    DefaultAzureCredential, 
    InteractiveBrowserCredential,
    AzureCliCredential,
    ClientSecretCredential,
    ChainedTokenCredential
)
from openai import OpenAI
from openai._models import FinalRequestOptions
from openai._types import Omit
from openai._utils import is_given

# Configure logging
logging.basicConfig(level=logging.INFO)

# Suppress OpenAI Assistants API deprecation warnings
# (Fabric Data Agents use the Assistants API model)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r".*Assistants API is deprecated.*"
)

# Optional: Load from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try importing synapse.ml.mlflow for Fabric authentication
try:
    from synapse.ml.mlflow import get_mlflow_env_config
    SYNAPSE_ML_AVAILABLE = True
except ImportError:
    SYNAPSE_ML_AVAILABLE = False


class FabricOpenAI(OpenAI):
    """
    Custom OpenAI client for Microsoft Fabric Data Agents.
    
    This client automatically sets up authentication and headers required
    for Fabric Data Agent API access.
    """
    
    def __init__(
        self,
        api_key: str = "",
        base_url: str = None,
        api_version: str = "2024-05-01-preview",
        token: str = None,
        **kwargs: t.Any,
    ) -> None:
        """
        Initialize the Fabric OpenAI client.
        
        Args:
            api_key (str): Not used but required by OpenAI client
            base_url (str): The base URL for the Fabric Data Agent
            api_version (str): The Fabric API version to use
            token (str): Bearer token for authorization
            **kwargs: Additional arguments to pass to the OpenAI client
        """
        self.api_version = api_version
        self.token = token
        default_query = kwargs.pop("default_query", {})
        default_query["api-version"] = self.api_version
        
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            default_query=default_query,
            **kwargs,
        )
    
    def _prepare_options(self, options: FinalRequestOptions) -> None:
        """
        Prepare request options by adding necessary headers.
        
        Args:
            options (FinalRequestOptions): The request options to prepare
        """
        headers: dict[str, str | Omit] = (
            {**options.headers} if is_given(options.headers) else {}
        )
        options.headers = headers
        
        # Add authorization header
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        # Add accept header if not present
        if "Accept" not in headers:
            headers["Accept"] = "application/json"
            
        # Add activity ID for tracing
        if "ActivityId" not in headers:
            correlation_id = str(uuid.uuid4())
            headers["ActivityId"] = correlation_id

        return super()._prepare_options(options)


class FabricDataAgentClient:
    """
    Client for calling Microsoft Fabric Data Agents from external applications.
    
    This client handles:
    - Managed Identity authentication for Azure deployments
    - Service Principal authentication for local development
    - Automatic token refresh
    - Bearer token management for API calls
    - Proper cleanup of resources
    - Support for both direct API and Assistants API patterns
    """
    
    def __init__(self, tenant_id: str = None, data_agent_url: str = None, 
                 client_id: str = None, client_secret: str = None,
                 use_managed_identity: bool = True, verify_url: bool = False,
                 api_version: str = "2024-05-01-preview"):
        """
        Initialize the Fabric Data Agent client.
        
        Args:
            tenant_id (str, optional): Your Azure tenant ID. If None, reads from env var TENANT_ID
            data_agent_url (str, optional): The published URL of your Fabric Data Agent. If None, reads from env var DATA_AGENT_URL
            client_id (str, optional): Service Principal client ID for auth. If None, reads from env var CLIENT_ID
            client_secret (str, optional): Service Principal client secret. If None, reads from env var CLIENT_SECRET
            use_managed_identity (bool): Whether to use Managed Identity in Azure (default: True)
            verify_url (bool): Whether to verify the Fabric Data Agent URL before using it (default: False)
            api_version (str): The Fabric API version to use (default: 2024-05-01-preview)
        """
        # Try to get values from environment if not provided
        self.tenant_id = tenant_id or os.environ.get("TENANT_ID")
        self.data_agent_url = data_agent_url or os.environ.get("DATA_AGENT_URL")
        self.client_id = client_id or os.environ.get("CLIENT_ID") or os.environ.get("AZURE_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("CLIENT_SECRET") or os.environ.get("AZURE_CLIENT_SECRET")
        self.use_managed_identity = use_managed_identity
        self.verify_url = verify_url
        self.api_version = api_version
        self.credential = None
        self.token = None
        self.client = None
        
        # Check for Fabric environment via SynapseML
        self.is_fabric_environment = SYNAPSE_ML_AVAILABLE
        self.mlflow_config = None
        if self.is_fabric_environment:
            try:
                print("Detected Fabric environment, getting mlflow config...")
                from synapse.ml.mlflow import get_mlflow_env_config
                self.mlflow_config = get_mlflow_env_config()
            except Exception as e:
                print(f"Failed to get mlflow config: {e}")
                self.is_fabric_environment = False
        
        # Validate inputs
        if not self.is_fabric_environment:
            # Only require tenant_id if not in Fabric environment
            if not self.tenant_id:
                raise ValueError("tenant_id is required (either as parameter or TENANT_ID env var)")
                
        if not self.data_agent_url:
            raise ValueError("data_agent_url is required (either as parameter or DATA_AGENT_URL env var)")
        
        print(f"Initializing Fabric Data Agent Client...")
        print(f"Data Agent URL: {self.data_agent_url}")
        if self.tenant_id:
            print(f"Tenant ID: {self.tenant_id}")
        
        # Parse and validate the URL structure
        try:
            url_parts = self.data_agent_url.split("/")
            if len(url_parts) < 8:
                print("⚠️ Warning: URL structure may be incorrect - not enough path segments")
            else:
                self.base_url = "/".join(url_parts[:3])  # https://api.fabric.microsoft.com
                self.version = url_parts[3]  # v1
                self.workspace_id = url_parts[5]  # {workspace-id}
                self.skill_id = url_parts[7]  # {skill-id}
                print(f"Workspace ID: {self.workspace_id}")
                print(f"AI Skill ID: {self.skill_id}")
        except Exception as e:
            print(f"⚠️ Warning: Could not parse URL structure: {e}")
        
        # Authenticate
        self._authenticate()
        
        # Verify the URL if requested
        if self.verify_url:
            self._verify_url()
    
    def _authenticate(self):
        """
        Perform authentication using Fabric MLflow env in Fabric environment,
        Managed Identity in Azure, or service principal for local development.
        """
        try:
            print("\n🔐 Starting authentication...")
            
            # Special handling for Fabric environment
            if self.is_fabric_environment and self.mlflow_config:
                print("Using Fabric MLflow environment for authentication...")
                # In Fabric environment, we don't need to create a credential
                # The token is already available in mlflow_config
                self.token_value = self.mlflow_config.driver_aad_token
                print("✅ Using token from Fabric environment")
                return
            
            # Check if we're running in Azure
            is_azure_environment = any([
                os.environ.get("WEBSITE_SITE_NAME") is not None,
                os.environ.get("FUNCTIONS_WORKER_RUNTIME") is not None,
                os.environ.get("AZURE_FUNCTIONS_ENVIRONMENT") is not None,
                os.environ.get("IDENTITY_ENDPOINT") is not None,  # Managed Identity indicator
                os.environ.get("MSI_ENDPOINT") is not None,  # Legacy Managed Identity indicator
            ])
            
            # Check if we're forcing managed identity locally for testing
            force_managed_identity_local = os.environ.get("FORCE_MANAGED_IDENTITY_LOCAL", "false").lower() == "true"
            
            if self.use_managed_identity and is_azure_environment:
                print("Azure environment detected - using Managed Identity authentication...")
                
                # Try to get client ID from environment variable if specified
                client_id = self.client_id or os.environ.get("AZURE_CLIENT_ID")
                
                if client_id:
                    print(f"Using User-Assigned Managed Identity with Client ID: {client_id}")
                    self.credential = ManagedIdentityCredential(client_id=client_id)
                else:
                    print("Using System-Assigned Managed Identity")
                    self.credential = ManagedIdentityCredential()
            
            else:
                # Local development or non-Azure environment
                print("Local environment detected - using Service Principal authentication")
                
                if self.client_id and self.client_secret:
                    print(f"Using Service Principal authentication with Client ID: {self.client_id}")
                    self.credential = ClientSecretCredential(
                        tenant_id=self.tenant_id,
                        client_id=self.client_id,
                        client_secret=self.client_secret
                    )
                else:
                    # Try fallback authentication methods
                    print("No Service Principal credentials provided - trying fallback authentication methods...")
                    
                    # Create a chained credential with multiple options
                    credentials = []
                    
                    # Try Azure CLI first (if user has run 'az login')
                    print("Trying Azure CLI credential...")
                    credentials.append(AzureCliCredential())
                    
                    # Then try DefaultAzureCredential
                    print("Adding DefaultAzureCredential as fallback...")
                    credentials.append(DefaultAzureCredential(exclude_interactive_browser_credential=False))
                    
                    self.credential = ChainedTokenCredential(*credentials)
            
            # Get initial token
            self._refresh_token()
            
            print("✅ Authentication successful!")
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print("\nTroubleshooting tips:")
            print("- For local development: ensure CLIENT_ID and CLIENT_SECRET environment variables are set")
            print("- For Azure deployment: ensure Managed Identity is enabled")
            print("- If using Azure CLI: run 'az login' first")
            print("- Check that the credentials have access to Microsoft Fabric resources")
            print("- If running in Fabric, ensure synapseml is installed: %pip install synapseml")
            raise

    def _refresh_token(self):
        """
        Refresh the authentication token.
        """
        try:
            print("🔄 Refreshing authentication token...")
            
            # If in Fabric environment, token is already available
            if self.is_fabric_environment and hasattr(self, 'token_value'):
                # Token is already set, no need to refresh
                return
                
            if self.credential is None:
                raise ValueError("No credential available")
                
            self.token = self.credential.get_token("https://api.fabric.microsoft.com/.default")
            self.token_value = self.token.token
            print(f"✅ Token obtained, expires at: {time.ctime(self.token.expires_on)}")
            
        except Exception as e:
            print(f"❌ Token refresh failed: {e}")
            raise
    
    def _get_openai_client(self) -> OpenAI:
        """
        Create an OpenAI client configured for Fabric Data Agent calls.
        
        Returns:
            OpenAI: Configured OpenAI client
        """
        # Check if we already created a client
        if self.client:
            # Check if token needs refresh (if we have an expiry time)
            if hasattr(self, 'token') and self.token and self.token.expires_on <= (time.time() + 300):
                self._refresh_token()
            return self.client
            
        # In Fabric environment, use our FabricOpenAI client
        if self.is_fabric_environment and hasattr(self, 'token_value'):
            self.client = FabricOpenAI(
                base_url=self.data_agent_url,
                token=self.token_value,
                api_version=self.api_version
            )
            return self.client
            
        # Otherwise use standard approach
        # Check if token needs refresh (if we have an expiry time)
        if hasattr(self, 'token') and self.token and self.token.expires_on <= (time.time() + 300):
            self._refresh_token()
            
        if not hasattr(self, 'token_value') or not self.token_value:
            raise ValueError("No authentication token available")
            
        # Create custom OpenAI client with token
        self.client = FabricOpenAI(
            base_url=self.data_agent_url,
            token=self.token_value,
            api_version=self.api_version
        )
        return self.client
        
    def _verify_url(self):
        """
        Verify that the Fabric Data Agent URL is accessible.
        """
        if not hasattr(self, 'base_url') or not hasattr(self, 'workspace_id') or not hasattr(self, 'skill_id'):
            print("⚠️ Could not verify URL - URL structure parsing failed")
            return False
            
        try:
            print("\n🔍 Verifying Fabric Data Agent URL...")
            
            # Ensure we have a token
            if not self.token:
                self._refresh_token()
                
            import requests
            headers = {
                "Authorization": f"Bearer {self.token.token}",
                "Content-Type": "application/json"
            }
            
            # Test the workspace endpoint
            workspace_url = f"{self.base_url}/{self.version}/workspaces/{self.workspace_id}"
            print(f"Testing workspace URL: {workspace_url}")
            
            response = requests.get(workspace_url, headers=headers)
            if response.status_code == 200:
                print("✅ Workspace exists and is accessible")
                workspace_data = response.json()
                if 'displayName' in workspace_data:
                    print(f"Workspace name: {workspace_data['displayName']}")
            else:
                print(f"❌ Could not access workspace: Status {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
            # Try different API patterns to find the working one
            api_patterns = [
                # Standard Data Agent pattern
                f"{self.base_url}/{self.version}/workspaces/{self.workspace_id}/dataagents/{self.skill_id}",
                # Items pattern
                f"{self.base_url}/{self.version}/workspaces/{self.workspace_id}/items/{self.skill_id}",
                # Old aiskills pattern
                f"{self.base_url}/{self.version}/workspaces/{self.workspace_id}/aiskills/{self.skill_id}/aiassistant/openai",
                # New dataagents pattern
                f"{self.base_url}/{self.version}/workspaces/{self.workspace_id}/dataagents/{self.skill_id}/openai",
                # Hybrid pattern
                f"{self.base_url}/{self.version}/workspaces/{self.workspace_id}/dataagents/{self.skill_id}/aiassistant/openai"
            ]
            
            working_urls = []
            for pattern in api_patterns:
                print(f"\nTesting API URL: {pattern}")
                try:
                    response = requests.get(pattern, headers=headers)
                    print(f"Status: {response.status_code}")
                    if response.status_code == 200:
                        print("✅ Accessible!")
                        working_urls.append(pattern)
                        print(f"Response: {response.text[:100]}...")
                    else:
                        print(f"❌ Not accessible: {response.text[:100]}...")
                except Exception as e:
                    print(f"Error: {e}")
            
            if working_urls:
                print("\n✅ Found working URLs:")
                for url in working_urls:
                    print(f"- {url}")
                
                # Find the one that matches our data_agent_url pattern or is closest
                self.working_url = None
                for url in working_urls:
                    if url.endswith("/openai"):
                        self.working_url = url
                        break
                
                if not self.working_url and working_urls:
                    self.working_url = working_urls[0]
                    
                if self.working_url:
                    print(f"\n✅ Selected working URL: {self.working_url}")
                    if self.working_url != self.data_agent_url:
                        print(f"⚠️ This differs from your configured URL: {self.data_agent_url}")
                        print("Consider updating your DATA_AGENT_URL environment variable.")
                    return True
            
            print("\n❌ No working OpenAI API endpoints found")
            print("\nTroubleshooting tips:")
            print("1. Verify the Data Agent is published in Microsoft Fabric portal")
            print("2. Check the 'Published URL' in the Fabric portal for the correct format")
            print("3. Ensure your account has permissions to access the Data Agent API")
            print("4. The Data Agent may need to be reconfigured or republished")
            print("5. Contact your Microsoft Fabric administrator for assistance")
            
            return False
                
        except Exception as e:
            print(f"❌ URL verification failed: {e}")
            return False
    
    def get_completion_using_assistants_api(self, prompt: str, model: str = "not used", **kwargs) -> Dict[str, Any]:
        """
        Get a completion from the Fabric Data Agent using Assistants API pattern.
        This is the recommended way to interact with Fabric Data Agents based on Microsoft's examples.
        
        Args:
            prompt (str): The question or prompt to send to the data agent
            model (str): Not used for Fabric Data Agents but required for compatibility
            **kwargs: Additional parameters to pass to the completions API
            
        Returns:
            Dict[str, Any]: Response from the Fabric Data Agent
        """
        try:
            print(f"\n📤 Sending completion request using Assistants API pattern...")
            
            client = self._get_openai_client()
            
            # Create assistant (not actually used by Fabric)
            assistant = client.beta.assistants.create(model=model)
            
            # Create thread
            thread = client.beta.threads.create()
            
            # Add message to thread
            message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )
            
            # Create run
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            print(f"⏳ Waiting for response (run ID: {run.id})...")
            
            # Wait for run to complete
            while run.status == "queued" or run.status == "in_progress":
                print(f"Status: {run.status}")
                time.sleep(2)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id,
                )
            
            print(f"✅ Run completed with status: {run.status}")
            
            # Get messages
            response = client.beta.threads.messages.list(
                thread_id=thread.id,
                order="asc"
            )
            
            # Clean up thread
            try:
                client.beta.threads.delete(thread_id=thread.id)
            except Exception as e:
                print(f"Warning: Failed to delete thread: {e}")
            
            # Return formatted response
            messages = [{"role": msg.role, "content": msg.content[0].text.value} 
                      for msg in response if hasattr(msg, 'content') and msg.content]
            
            return {
                "choices": [{
                    "message": messages[-1] if messages else {"role": "assistant", "content": "No response received"},
                    "finish_reason": "stop"
                }],
                "created": int(time.time()),
                "id": run.id,
                "model": model,
                "object": "chat.completion",
                "all_messages": messages
            }
            
        except Exception as e:
            print(f"❌ Error getting completion: {e}")
            
            # Additional context for troubleshooting
            print("\nMake sure your Data Agent is:")
            print("1. Published in the Microsoft Fabric portal")
            print("2. Configured with an OpenAI-compatible API")
            print("3. Accessible with your current credentials")
            print("4. Try using the URL verification tool: client = FabricDataAgentClient(verify_url=True)")
            
            raise
    
    def ask(self, prompt: str, model: str = "gpt-4", **kwargs) -> str:
        """
        Ask a question to the Fabric Data Agent and get a string response.
        This is a simpler interface that returns just the response text.
        
        Args:
            prompt (str): The question or prompt to send to the data agent
            model (str): The model to use (default: "gpt-4")
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            str: The response from the Fabric Data Agent
        """
        try:
            # Use the Assistants API pattern for better reliability
            response = self.get_completion(prompt=prompt, model=model, use_assistants_api=True, **kwargs)
            
            # Extract the text response from the appropriate part of the structure
            if "all_messages" in response and response["all_messages"]:
                # Get the last assistant message
                assistant_messages = [msg for msg in response["all_messages"] if msg["role"] == "assistant"]
                if assistant_messages:
                    return assistant_messages[-1]["content"]
            
            # Fallback to choices structure
            if "choices" in response and response["choices"]:
                message = response["choices"][0].get("message", {})
                if isinstance(message, dict) and "content" in message:
                    return message["content"]
                
            # Further fallback
            return str(response)
            
        except Exception as e:
            # Log the error but return a string (don't raise)
            error_msg = f"Error in ask method: {str(e)}"
            print(error_msg)
            return f"I encountered an error while processing your request: {str(e)}"
    
    def get_completion(self, messages: list = None, prompt: str = None, model: str = "gpt-4", 
                       use_assistants_api: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Get a completion from the Fabric Data Agent.
        
        Args:
            messages (list): List of message dictionaries (system, user, assistant)
            prompt (str): Alternative to messages - a single prompt string
            model (str): The model to use for completions (default: "gpt-4")
            use_assistants_api (bool): Whether to use Assistants API pattern (default: True)
            **kwargs: Additional parameters to pass to the completions API
            
        Returns:
            Dict[str, Any]: Response from the Fabric Data Agent
        """
        # Handle single prompt string
        if prompt and not messages:
            if use_assistants_api:
                return self.get_completion_using_assistants_api(prompt, model, **kwargs)
            else:
                messages = [{"role": "user", "content": prompt}]
                
        # Use Assistants API if requested (and we have a simple user message)
        if use_assistants_api and messages and len(messages) == 1 and messages[0]["role"] == "user":
            return self.get_completion_using_assistants_api(messages[0]["content"], model, **kwargs)
            
        # Otherwise use direct OpenAI client API
        # Check if we found a working URL during verification
        if hasattr(self, 'working_url') and self.working_url:
            # Use the working URL instead
            data_agent_url = self.working_url
        else:
            data_agent_url = self.data_agent_url
        
        try:
            # Get the OpenAI client
            client = self._get_openai_client()
            
            # Use chat completions API directly
            print(f"Sending completion request to: {data_agent_url}")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            
            # Convert response to dictionary if needed
            if hasattr(response, 'model_dump'):
                return response.model_dump()
            else:
                return response
            
        except Exception as e:
            print(f"❌ Error getting completion: {e}")
            
            # Try direct HTTP request as fallback
            try:
                import requests
                
                print(f"Trying direct HTTP request as fallback...")
                
                # Ensure we have a token
                if not hasattr(self, 'token_value') or not self.token_value:
                    self._refresh_token()
                
                # Append /chat/completions if not already present
                if not data_agent_url.endswith("/chat/completions"):
                    if data_agent_url.endswith("/openai"):
                        data_agent_url = f"{data_agent_url}/chat/completions"
                    else:
                        data_agent_url = f"{data_agent_url}/openai/chat/completions"
                
                print(f"Sending completion request to: {data_agent_url}")
                
                headers = {
                    "Authorization": f"Bearer {self.token_value}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "messages": messages,
                    "model": model,
                    **kwargs
                }
                
                response = requests.post(data_agent_url, headers=headers, json=data)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = f"API Error: {response.status_code} - {response.text}"
                    print(error_msg)
                    
                    # Provide helpful troubleshooting information
                    if response.status_code == 404:
                        print("\nTroubleshooting tips for 404 Not Found:")
                        print("1. Verify your Data Agent is published in Microsoft Fabric")
                        print("2. Get the exact URL from the Fabric portal 'Published URL'")
                        print("3. Try using the URL verification tool: client = FabricDataAgentClient(verify_url=True)")
                        print("4. Check if your token has permission to access this API")
                        print("5. Try again with use_assistants_api=True")
                    
                    raise ValueError(error_msg)
            except Exception as fallback_error:
                print(f"Fallback request also failed: {fallback_error}")
                
                # Additional context for troubleshooting
                print("\nMake sure your Data Agent is:")
                print("1. Published in the Microsoft Fabric portal")
                print("2. Configured with an OpenAI-compatible API")
                print("3. Accessible with your current credentials")
                print("4. Try using the URL verification tool: client = FabricDataAgentClient(verify_url=True)")
                print("5. Try again with use_assistants_api=True (recommended by Microsoft)")
                
                # Re-raise the original error
                raise e