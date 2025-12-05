from fastapi import APIRouter, HTTPException, status
import logging

from ..models.schemas import SummarizeRequest, SummarizeResponse
from ..services.llm_service import llm_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/summarize_note", response_model=SummarizeResponse)
async def summarize_note(request: SummarizeRequest):
    try:
        result = await llm_service.summarize_medical_note(request.text)
        return SummarizeResponse(**result)
    except Exception as e:
        logger.error(f"Error summarizing note: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to summarize note: {str(e)}"
        )
