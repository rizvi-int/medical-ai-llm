from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .core.config import settings
from .db.base import init_db
from .api import health, documents, llm, rag, agent, fhir, chat

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")
    await init_db()
    logger.info("Database initialized")

    # Auto-seed database with example notes if empty
    try:
        from pathlib import Path
        from sqlalchemy import select, func
        from .db.base import AsyncSessionLocal
        from .models.document import Document

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(func.count(Document.id)))
            count = result.scalar()

            if count == 0:
                logger.info("Database is empty. Seeding with example SOAP notes...")
                example_notes_dir = Path(__file__).resolve().parent.parent.parent / "example_notes"

                if example_notes_dir.exists():
                    soap_files = sorted(example_notes_dir.glob("soap_*.txt"))
                    for soap_file in soap_files:
                        content = soap_file.read_text()
                        title = f"Medical Note - {soap_file.stem.replace('soap_', 'Case ')}"
                        document = Document(title=title, content=content)
                        session.add(document)
                        logger.info(f"Added: {title}")

                    await session.commit()
                    logger.info(f"Successfully seeded {len(soap_files)} documents to SQL database")

                    # Index documents in Qdrant vector store
                    try:
                        from .services.rag_service import get_rag_service

                        result = await session.execute(select(Document))
                        documents = result.scalars().all()
                        doc_dicts = [
                            {"id": doc.id, "title": doc.title, "content": doc.content}
                            for doc in documents
                        ]

                        await get_rag_service().index_documents(doc_dicts)
                        logger.info(f"Successfully indexed {len(doc_dicts)} documents to Qdrant vector store")
                    except Exception as e:
                        logger.warning(f"Could not index documents to Qdrant (service may not be available): {str(e)}")
                else:
                    logger.warning(f"Example notes directory not found: {example_notes_dir}")
            else:
                logger.info(f"Database already has {count} documents")
    except Exception as e:
        logger.error(f"Error during database seeding: {str(e)}")

    yield
    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(llm.router, tags=["llm"])
app.include_router(rag.router, tags=["rag"])
app.include_router(agent.router, tags=["agent"])
app.include_router(fhir.router, tags=["fhir"])
app.include_router(chat.router, tags=["chatbot"])


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
    }


def main():
    import uvicorn
    uvicorn.run(
        "medical_notes_processor.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
