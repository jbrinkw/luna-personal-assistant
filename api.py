import sys
import os

# Add the project root to the Python path
# This assumes api.py is in the root directory or a subdirectory.
# Adjust the path if your structure is different.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import traceback

# Import the ChefByteChat class from your existing app module
try:
    from app import ChefByteChat
except ImportError as e:
    print(f"Error importing ChefByteChat: {e}")
    print("Please ensure app.py is in the Python path or the same directory.")
    # You might want to handle this more gracefully or raise the error
    # depending on your deployment strategy.
    sys.exit(1) # Exit if ChefByteChat cannot be imported


app = FastAPI(
    title="ChefByte API",
    description="API proxy for interacting with the ChefByte cooking assistant.",
    version="0.1.0",
)

# --- Global ChefByteChat Instance ---
# We create a single instance when the API starts.
# This instance will maintain the conversation state internally.
try:
    print("Initializing ChefByteChat for API...")
    chef_chat_instance = ChefByteChat()
    print("ChefByteChat initialized successfully for API.")
except Exception as e:
    print(f"[CRITICAL API ERROR] Failed to initialize ChefByteChat: {e}")
    print(traceback.format_exc())
    # Handle the error appropriately - maybe the API shouldn't start
    # For now, we'll let it potentially fail later if accessed
    chef_chat_instance = None # Set to None if initialization fails

# --- Pydantic Models for Request/Response ---
class UserInput(BaseModel):
    text: str

class ChatResponse(BaseModel):
    text: str

class ResetResponse(BaseModel):
    message: str

# --- API Endpoints ---

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(user_input: UserInput):
    """
    Processes a user message through ChefByteChat and returns the response.
    Maintains conversation history within the ChefByteChat instance.
    """
    if not chef_chat_instance:
        raise HTTPException(status_code=500, detail="ChefByteChat service is not available due to initialization error.")
        
    if not user_input.text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")
        
    try:
        response_text = chef_chat_instance.process_message(user_input.text)
        return ChatResponse(text=response_text)
    except Exception as e:
        print(f"Error processing message in /chat endpoint: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

@app.post("/reset", response_model=ResetResponse)
async def reset_endpoint():
    """
    Resets the conversation history within the ChefByteChat instance.
    """
    if not chef_chat_instance:
         raise HTTPException(status_code=500, detail="ChefByteChat service is not available due to initialization error.")
         
    try:
        chef_chat_instance.reset_conversation()
        return ResetResponse(message="Conversation history has been reset.")
    except Exception as e:
        print(f"Error resetting conversation in /reset endpoint: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An internal error occurred during reset: {str(e)}")

# --- Cleanup on Shutdown (Optional but Recommended) ---
@app.on_event("shutdown")
def shutdown_event():
    print("API shutting down. Closing ChefByteChat resources...")
    if chef_chat_instance:
        chef_chat_instance.close()
    print("ChefByteChat resources closed.") 