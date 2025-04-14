import sys
import os
from dotenv import load_dotenv # Added dotenv import

# Add the project root to the Python path
# This assumes api.py is in the root directory or a subdirectory.
# Adjust the path if your structure is different.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# Also add parent if db/tools are outside current dir? Adjust as needed.
parent_dir = os.path.dirname(project_root)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

load_dotenv() # Load environment variables like OPENAI_API_KEY

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import traceback
from typing import List, Dict, Any

# Import the necessary components from agent_app.py
try:
    # Assuming agent_app defines these globally or makes them accessible
    from agent_app import orchestrator_agent, Runner
    # We might need to explicitly initialize DB or other resources if not handled by agents/runner
    # from db.db_functions import init_tables # Optional: if direct DB access needed
    print("Successfully imported components from agent_app.")
except ImportError as e:
    print(f"Error importing from agent_app: {e}")
    print(f"Current sys.path: {sys.path}")
    print("Please ensure agent_app.py and its dependencies (agents, tools, db) are accessible.")
    sys.exit(1) # Exit if core components cannot be imported
except Exception as e:
    print(f"An unexpected error occurred during import/setup: {e}")
    print(traceback.format_exc())
    sys.exit(1)


app = FastAPI(
    title="ChefByte Agent API",
    description="API proxy for interacting with the ChefByte agent system.",
    version="0.2.2", # Updated version
)

# --- Global Agent Instance (Orchestrator) ---
# The orchestrator agent is imported directly.
# Runner.run_sync is a static method, so no global instance needed for it.
if not orchestrator_agent:
    print("[CRITICAL API ERROR] Failed to load orchestrator_agent.")
    # Potentially raise an error or prevent FastAPI from starting
    # For now, rely on endpoint checks

# --- Global Conversation History ---
# Single global conversation history (simpler than session-based for testing)
conversation_history: List[Dict[str, Any]] = []

# --- Pydantic Models for Request/Response ---
class UserInput(BaseModel):
    text: str

class ChatResponse(BaseModel):
    text: str # Assuming the agent runner returns a string in final_output

class ResetResponse(BaseModel):
    message: str

# --- API Endpoints ---

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(user_input: UserInput):
    """
    Processes a user message through the ChefByte agent system.
    Maintains a single global conversation history for all requests.
    """
    global conversation_history
    
    if not orchestrator_agent:
        raise HTTPException(status_code=503, detail="ChefByte agent service is unavailable (failed to load).")

    if not user_input.text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")
    
    try:
        print(f"Processing message: '{user_input.text[:50]}...'")
        
        # If we have existing history, append new message and pass full history
        if conversation_history:
            conversation_history.append({"role": "user", "content": user_input.text})
            result = await Runner.run(orchestrator_agent, conversation_history)
        else:
            # For the first message, we can just use the text (matches agent_app.py behavior)
            result = await Runner.run(orchestrator_agent, user_input.text)
        
        # Get the response text
        response_text = result.final_output if result and result.final_output else "Sorry, I couldn't process that."
        
        # Update the global conversation history with the full conversation from the runner
        conversation_history = result.to_input_list() if hasattr(result, "to_input_list") else conversation_history
        
        print(f"Agent response: '{response_text[:100]}...'")
        return ChatResponse(text=response_text)
    except Exception as e:
        print(f"Error processing message in /chat endpoint via Agent Runner: {e}")
        print(traceback.format_exc())
        # Provide a more generic error to the client
        raise HTTPException(status_code=500, detail="An internal error occurred while processing your request.")

@app.post("/reset", response_model=ResetResponse)
async def reset_endpoint():
    """
    Resets the global conversation history.
    """
    global conversation_history
    conversation_history = []
    message = "Global conversation history has been reset."
    print(message)
    return ResetResponse(message=message)

@app.get("/history")
async def get_history():
    """
    Development endpoint to view the current conversation history.
    """
    return {"history": conversation_history}

# --- Cleanup on Shutdown (Optional) ---
@app.on_event("shutdown")
def shutdown_event():
    # Clear conversation history
    global conversation_history
    conversation_history = []
    print("API shutting down. Cleared conversation history.") 