"""Demo OpenAI API Server with 'pie' model
Mimics OpenAI API endpoints but always returns 'pie'
"""
from fastapi import FastAPI, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import uvicorn
import json
import time
import os
import secrets
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv, set_key, find_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")
    set_key = None
    find_dotenv = None

# Get or generate API key
def get_or_generate_api_key() -> str:
    """Get API key from environment or generate and save a new one"""
    api_key = os.getenv("AGENT_API_KEY")
    
    if api_key:
        print(f"[AUTH] Using existing AGENT_API_KEY from environment")
        return api_key
    
    # Generate new API key
    api_key = f"sk-pie-{secrets.token_urlsafe(32)}"
    print(f"[AUTH] No AGENT_API_KEY found, generated new key: {api_key}")
    
    # Try to save to .env file
    if set_key and find_dotenv:
        try:
            env_file = find_dotenv()
            if not env_file:
                # Create .env file if it doesn't exist
                env_file = Path(".env")
                env_file.touch()
                env_file = str(env_file)
            
            set_key(env_file, "AGENT_API_KEY", api_key, quote_mode="never")
            print(f"[AUTH] Saved AGENT_API_KEY to {env_file}")
        except Exception as e:
            print(f"[AUTH] Warning: Could not save API key to .env file: {e}")
            print(f"[AUTH] Please manually add to .env: AGENT_API_KEY={api_key}")
    else:
        print(f"[AUTH] Please manually add to .env: AGENT_API_KEY={api_key}")
    
    return api_key

# Initialize API key
API_KEY = get_or_generate_api_key()

# Get public URL from environment
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8000")
print(f"[SERVER] Public URL: {PUBLIC_URL}")

# Security scheme
security = HTTPBearer()

app = FastAPI(title="Pie API Server", description="Demo OpenAI-compatible API that returns 'pie'")

# API Key validation
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify the API key from the Authorization header"""
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Request models
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    
class CompletionRequest(BaseModel):
    model: str
    prompt: Union[str, List[str]]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False

# Root endpoint (no auth required)
@app.get("/")
async def root():
    return {
        "message": "Pie API Server - OpenAI compatible",
        "base_url": PUBLIC_URL,
        "endpoints": [
            "/v1/models",
            "/v1/chat/completions",
            "/v1/completions"
        ],
        "auth": "Bearer token required (use AGENT_API_KEY)"
    }

# List models endpoint
@app.get("/v1/models")
async def list_models(api_key: str = Security(verify_api_key)):
    return {
        "object": "list",
        "data": [
            {
                "id": "pie",
                "object": "model",
                "created": 1234567890,
                "owned_by": "pie-org",
                "permission": [],
                "root": "pie",
                "parent": None
            }
        ]
    }

# Get model details
@app.get("/v1/models/{model_id}")
async def get_model(model_id: str, api_key: str = Security(verify_api_key)):
    if model_id != "pie":
        raise HTTPException(status_code=404, detail="Model not found")
    
    return {
        "id": "pie",
        "object": "model",
        "created": 1234567890,
        "owned_by": "pie-org"
    }

# Chat completions endpoint
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, api_key: str = Security(verify_api_key)):
    if request.model != "pie":
        raise HTTPException(status_code=404, detail="Model not found. Only 'pie' model is available.")
    
    # Non-streaming response
    if not request.stream:
        return {
            "id": f"chatcmpl-pie{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "pie",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "pie"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 1,
                "total_tokens": 11
            }
        }
    
    # Streaming response
    async def generate_stream():
        # Send the word "pie"
        chunk = {
            "id": f"chatcmpl-pie{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "pie",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": "pie"
                    },
                    "finish_reason": None
                }
            ]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        
        # Send final chunk
        final_chunk = {
            "id": f"chatcmpl-pie{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "pie",
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")

# Legacy completions endpoint
@app.post("/v1/completions")
async def completions(request: CompletionRequest, api_key: str = Security(verify_api_key)):
    if request.model != "pie":
        raise HTTPException(status_code=404, detail="Model not found. Only 'pie' model is available.")
    
    # Non-streaming response
    if not request.stream:
        return {
            "id": f"cmpl-pie{int(time.time())}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": "pie",
            "choices": [
                {
                    "text": "pie",
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 1,
                "total_tokens": 6
            }
        }
    
    # Streaming response
    async def generate_stream():
        chunk = {
            "id": f"cmpl-pie{int(time.time())}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": "pie",
            "choices": [
                {
                    "text": "pie",
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": None
                }
            ]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        
        final_chunk = {
            "id": f"cmpl-pie{int(time.time())}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": "pie",
            "choices": [
                {
                    "text": "",
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    print("="*60)
    print("🥧 Pie API Server Starting...")
    print("="*60)
    print(f"Public URL: {PUBLIC_URL}")
    print(f"API Key: {API_KEY}")
    print(f"Model available: pie")
    print("\nEndpoints:")
    print(f"  - GET  {PUBLIC_URL}/v1/models")
    print(f"  - POST {PUBLIC_URL}/v1/chat/completions")
    print(f"  - POST {PUBLIC_URL}/v1/completions")
    print("\nAuthentication:")
    print(f"  Add header: Authorization: Bearer {API_KEY}")
    print("="*60)
    print("\nAll requests will return 'pie' 🥧\n")
    
    uvicorn.run(app, host=host, port=port)

