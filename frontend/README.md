# Charter VIP Chatbot

A premium AI-powered customer service chatbot for Charter Communications, featuring a clean Next.js frontend and FastAPI backend connected to Azure AI Foundry.

## Features

- **Professional Charter-branded UI** with navy blue and bright blue color scheme
- **Multi-turn conversation support** with message history
- **Real-time typing indicators** and smooth animations
- **Responsive design** optimized for desktop and mobile
- **Azure AI Foundry integration** for intelligent responses
- **FastAPI backend** with CORS support and error handling
- **Fallback responses** when AI services are unavailable

## Architecture

### Frontend (Next.js)
- Modern React components with TypeScript
- Tailwind CSS with custom Charter theme
- Real-time chat interface with scroll management
- Responsive design following Charter brand guidelines

### Backend (FastAPI)
- RESTful API with automatic documentation
- Azure AI Foundry Project endpoint integration
- Conversation management and user tracking
- Comprehensive error handling and logging

## Getting Started

### Prerequisites
- Node.js 18+ and npm/yarn
- Python 3.8+ and pip
- Azure AI Foundry Project credentials

### Frontend Setup
\`\`\`bash
npm install
npm run dev
\`\`\`

### Backend Setup
\`\`\`bash
cd scripts
pip install -r requirements.txt

# Set environment variables
export AZURE_AI_FOUNDRY_ENDPOINT="your-endpoint-url"
export AZURE_AI_FOUNDRY_KEY="your-api-key"
export AZURE_AI_PROJECT_NAME="charter-vip-chatbot"

# Run the FastAPI server
python fastapi-backend.py
\`\`\`

### Environment Variables
Create a `.env.local` file in the root directory:
\`\`\`
AZURE_AI_FOUNDRY_ENDPOINT=your-endpoint-url
AZURE_AI_FOUNDRY_KEY=your-api-key
AZURE_AI_PROJECT_NAME=charter-vip-chatbot
\`\`\`

## API Endpoints

- `GET /` - API status and version
- `GET /health` - Health check with Azure AI status
- `POST /chat` - Main chat endpoint

### Chat Request Format
\`\`\`json
{
  "message": "I need help with my internet service",
  "conversation_id": "optional-conversation-id",
  "user_id": "optional-user-id"
}
\`\`\`

### Chat Response Format
\`\`\`json
{
  "response": "I can help you with internet issues...",
  "conversation_id": "conv_12345",
  "timestamp": "2024-01-15T10:30:00"
}
\`\`\`

## Charter Services Supported

- **Spectrum Internet**: High-speed broadband support
- **Spectrum TV**: Cable television assistance
- **Spectrum Voice**: Phone service help
- **Billing & Account Management**: Payment and account support

## Deployment

### Frontend (Vercel)
\`\`\`bash
npm run build
# Deploy to Vercel or your preferred platform
\`\`\`

### Backend (Docker/Cloud)
\`\`\`dockerfile
FROM python:3.9-slim
COPY scripts/ /app/
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["uvicorn", "fastapi-backend:app", "--host", "0.0.0.0", "--port", "8000"]
\`\`\`

## Development Notes

- The frontend includes fallback responses when the backend is unavailable
- Azure AI integration uses the Foundry Agent Service and model access
- All Charter branding follows official brand guidelines
- CORS is configured for local development and production domains

## Support

For technical issues or questions about the Charter VIP Chatbot, please contact the development team or refer to the Azure AI Foundry documentation.
