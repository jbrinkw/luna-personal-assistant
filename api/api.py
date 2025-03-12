from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app import LunaAssistant

app = FastAPI(title="Luna Personal Assistant API")
luna = LunaAssistant()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    router_output: dict
    response_parts: list[str]

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        result = luna.process_message(request.message)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
async def reset_conversation():
    luna.reset_conversation()
    return {"status": "success", "message": "Conversation history reset"}