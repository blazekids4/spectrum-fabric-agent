# Import the app from your backend
from backend.app import app

# Export the app directly for Vercel
# Vercel expects the FastAPI app to be available as 'app'
__all__ = ['app']