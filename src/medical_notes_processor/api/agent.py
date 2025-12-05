from fastapi import APIRouter, HTTPException, status
import logging

from ..models.schemas import ExtractStructuredRequest, ExtractStructuredResponse
from ..agents.extraction_agent import extraction_agent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/extract_structured", response_model=ExtractStructuredResponse)
async def extract_structured_data(request: ExtractStructuredRequest):
    try:
        structured_data = await extraction_agent.extract_structured_data(request.text)
        return ExtractStructuredResponse(structured_data=structured_data)
    except Exception as e:
        logger.error(f"Error extracting structured data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract structured data: {str(e)}"
        )
