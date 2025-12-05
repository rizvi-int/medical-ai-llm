from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import logging

from ..services.chatbot_service import get_chatbot_service

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    note_id: Optional[int] = None


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the medical AI assistant using linear RAG pipeline.

    Pipeline Architecture:
    1. Load note content (if note_id provided)
    2. Generate note summary
    3. Retrieve relevant chunks from vector store
    4. Construct prompt with all context
    5. Generate answer with strict constraints

    Request:
        message: User's question
        note_id: Optional document ID for focused context

    The chatbot answers based ONLY on provided context.
    No agent tool calling - deterministic pipeline execution.
    """
    try:
        chatbot = get_chatbot_service()
        response_text = await chatbot.chat(
            user_message=request.message,
            note_id=request.note_id
        )

        return ChatResponse(response=response_text)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(e)}"
        )
