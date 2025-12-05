from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
from collections import defaultdict

from ..services.chatbot_service import get_chatbot_service

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple in-memory conversation storage (session_id -> messages)
conversations: Dict[str, List[Dict[str, str]]] = defaultdict(list)


class ChatRequest(BaseModel):
    message: str
    note_id: Optional[int] = None
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the medical AI assistant with conversation memory.

    Features:
    - Maintains conversation history per session
    - Auto-detects document IDs from messages
    - Supports summarization and code extraction
    - Remembers context from previous messages

    Request:
        message: User's question
        note_id: Optional document ID for focused context
        session_id: Optional session ID for conversation tracking (default: "default")
    """
    try:
        session_id = request.session_id or "default"

        # Get conversation history
        history = conversations[session_id]

        chatbot = get_chatbot_service()
        response_text = await chatbot.chat(
            user_message=request.message,
            note_id=request.note_id,
            conversation_history=history
        )

        # Store in conversation history
        conversations[session_id].append({"role": "user", "content": request.message})
        conversations[session_id].append({"role": "assistant", "content": response_text})

        # Keep last 20 messages to prevent memory bloat
        if len(conversations[session_id]) > 20:
            conversations[session_id] = conversations[session_id][-20:]

        return ChatResponse(response=response_text, session_id=session_id)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(e)}"
        )


@router.post("/chat/reset")
async def reset_conversation(session_id: str = "default"):
    """Reset conversation history for a session."""
    if session_id in conversations:
        del conversations[session_id]
    return {"message": f"Conversation reset for session {session_id}"}
