"""
Charter VIP Chatbot FastAPI Backend
This script provides the backend API for the Charter VIP Chatbot
Connected to Azure AI Foundry Project endpoint
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx
import json
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Charter VIP Chatbot API",
    description="Backend API for Charter VIP Assistant powered by Azure AI Foundry",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str

# Azure AI Foundry configuration
AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
AZURE_AI_KEY = os.getenv("AZURE_AI_FOUNDRY_KEY")
AZURE_AI_PROJECT = os.getenv("AZURE_AI_PROJECT_NAME")

# Charter-specific system prompt
CHARTER_SYSTEM_PROMPT = """
You are the Charter VIP Assistant, a premium AI-powered customer service representative for Charter Communications. 

Your role:
- Provide exceptional customer service for Charter Spectrum services (Internet, TV, Phone)
- Handle billing inquiries, technical support, and account management
- Maintain a professional, helpful, and knowledgeable tone
- Prioritize customer satisfaction and quick resolution

Charter Services:
- Spectrum Internet: High-speed broadband with various speed tiers
- Spectrum TV: Cable television with hundreds of channels and on-demand
- Spectrum Voice: Digital phone service with unlimited calling
- Spectrum Mobile: Wireless service for existing customers

Key Guidelines:
- Always identify yourself as Charter VIP Assistant
- Be concise but thorough in responses
- Offer to escalate complex issues to human agents when appropriate
- Provide accurate information about Charter services and policies
- Maintain customer privacy and security standards
"""

async def call_azure_ai_foundry(message: str, conversation_id: str = None) -> str:
    """
    Call Azure AI Foundry Project endpoint for chat completion
    """
    if not AZURE_AI_ENDPOINT or not AZURE_AI_KEY:
        logger.warning("Azure AI credentials not configured, using fallback response")
        return generate_fallback_response(message)
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AZURE_AI_KEY}",
            "X-Project-Name": AZURE_AI_PROJECT or "charter-vip-chatbot"
        }
        
        payload = {
            "messages": [
                {"role": "system", "content": CHARTER_SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            "max_tokens": 500,
            "temperature": 0.7,
            "conversation_id": conversation_id
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AZURE_AI_ENDPOINT}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                logger.error(f"Azure AI API error: {response.status_code} - {response.text}")
                return generate_fallback_response(message)
                
    except Exception as e:
        logger.error(f"Error calling Azure AI Foundry: {str(e)}")
        return generate_fallback_response(message)

def generate_fallback_response(message: str) -> str:
    """
    Generate fallback responses when Azure AI is unavailable
    """
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['billing', 'bill', 'payment', 'charge']):
        return """I can help you with billing questions. Charter Spectrum offers:
        
• Online account management at spectrum.com
• Autopay options to avoid late fees  
• Detailed billing statements with service breakdowns
• Multiple payment methods including online, phone, and in-person

Would you like me to help you understand your current charges or set up a payment method?"""
    
    elif any(word in message_lower for word in ['internet', 'wifi', 'slow', 'connection']):
        return """I can assist with internet and WiFi issues. Charter Spectrum Internet offers:

• High-speed broadband up to 1 Gig speeds
• Free WiFi router and security suite
• 24/7 technical support
• No data caps on residential plans

Are you experiencing slow speeds, connection drops, or need help optimizing your WiFi setup?"""
    
    elif any(word in message_lower for word in ['tv', 'cable', 'channels', 'remote']):
        return """I can help with TV and cable services. Charter Spectrum TV provides:

• 125+ channels in the Select package
• Thousands of On Demand titles
• Spectrum TV App for streaming on devices
• Cloud DVR service available

Are you having issues with specific channels, your cable box, or looking to upgrade your package?"""
    
    elif any(word in message_lower for word in ['phone', 'voice', 'calling']):
        return """I can assist with phone service. Charter Spectrum Voice offers:

• Unlimited local and long distance calling
• Advanced calling features like voicemail and call forwarding
• Keep your existing phone number
• Crystal clear digital voice quality

Do you need help with voicemail setup, call features, or service activation?"""
    
    else:
        return """Hello! I'm your Charter VIP Assistant. I'm here to provide premium support for all your Charter Spectrum services including:

• Internet & WiFi support
• TV & Cable assistance  
• Phone service help
• Billing & account management

How can I assist you today? Please let me know what specific service or issue you'd like help with."""

@app.get("/")
async def root():
    return {
        "message": "Charter VIP Chatbot API",
        "status": "active",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "azure_ai_configured": bool(AZURE_AI_ENDPOINT and AZURE_AI_KEY)
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint for Charter VIP Assistant
    """
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or f"conv_{hash(request.message + str(request.user_id))}"
        
        # Get AI response
        ai_response = await call_azure_ai_foundry(request.message, conversation_id)
        
        if not ai_response:
            ai_response = "I apologize, but I'm having trouble processing your request right now. Please try again in a moment, or contact Charter support directly at 1-833-267-6094."
        
        return ChatResponse(
            response=ai_response,
            conversation_id=conversation_id,
            timestamp=str(pd.Timestamp.now())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "fastapi-backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
