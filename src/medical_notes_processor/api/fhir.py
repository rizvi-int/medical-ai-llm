from fastapi import APIRouter, HTTPException, status
import logging

from ..models.schemas import ToFHIRRequest, ToFHIRResponse
from ..services.fhir_service import fhir_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/to_fhir", response_model=ToFHIRResponse)
async def convert_to_fhir(request: ToFHIRRequest):
    try:
        fhir_bundle = fhir_service.convert_to_fhir(request.structured_data)
        return ToFHIRResponse(fhir_bundle=fhir_bundle)
    except Exception as e:
        logger.error(f"Error converting to FHIR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert to FHIR: {str(e)}"
        )
