from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from ..models.schemas import QuestionRequest, QuestionResponse
from ..services.rag_service import get_rag_service
from ..db.base import get_db
from ..models.document import Document

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/index_documents")
async def index_documents(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Document))
        documents = result.scalars().all()

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No documents found in database to index"
            )

        doc_dicts = [
            {"id": doc.id, "title": doc.title, "content": doc.content}
            for doc in documents
        ]

        await get_rag_service().index_documents(doc_dicts)

        return {
            "message": f"Successfully indexed {len(documents)} documents",
            "document_count": len(documents)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index documents: {str(e)}"
        )


@router.post("/answer_question", response_model=QuestionResponse)
async def answer_question(request: QuestionRequest):
    try:
        result = await get_rag_service().answer_question(request.question)
        return QuestionResponse(**result)
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {str(e)}"
        )
