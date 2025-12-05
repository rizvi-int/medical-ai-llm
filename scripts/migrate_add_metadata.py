#!/usr/bin/env python3
"""
Migration script to add patient_name and encounter_date columns to documents table
and populate them from existing documents.
"""
import asyncio
from sqlalchemy import text, select

# Import from the correct location based on environment
try:
    # Try Docker container path first
    from medical_notes_processor.db.base import AsyncSessionLocal
    from medical_notes_processor.agents.extraction_agent import extraction_agent
    from medical_notes_processor.models.document import Document
except ModuleNotFoundError:
    # Fall back to local development path
    from src.medical_notes_processor.db.base import AsyncSessionLocal
    from src.medical_notes_processor.agents.extraction_agent import extraction_agent
    from src.medical_notes_processor.models.document import Document


async def migrate():
    """Populate patient_name and encounter_date metadata."""
    print("Starting migration...")

    async with AsyncSessionLocal() as db:
        try:
            # Columns should already exist from the model definition
            # Just populate the data

            # Get all documents
            result = await db.execute(select(Document.id, Document.content))
            documents = result.all()
            print(f"Found {len(documents)} documents to process")

            # Extract and update metadata for each document
            for doc_id, content in documents:
                print(f"Processing document {doc_id}...")
                try:
                    # Extract structured data
                    structured_data = await extraction_agent.extract_structured_data(content)

                    # Get patient name and encounter date
                    patient_name = None
                    encounter_date = None

                    if structured_data.patient and structured_data.patient.name:
                        patient_name = structured_data.patient.name

                    if structured_data.encounter_date:
                        encounter_date = structured_data.encounter_date

                    # Update document
                    await db.execute(
                        text("""
                            UPDATE documents
                            SET patient_name = :patient_name,
                                encounter_date = :encounter_date
                            WHERE id = :id
                        """),
                        {"patient_name": patient_name, "encounter_date": encounter_date, "id": doc_id}
                    )
                    print(f"  ✓ Updated doc {doc_id}: {patient_name or 'N/A'}, {encounter_date or 'N/A'}")
                except Exception as e:
                    print(f"  ✗ Error processing doc {doc_id}: {str(e)}")

            await db.commit()
            print("\nMigration completed successfully!")

        except Exception as e:
            print(f"Migration failed: {str(e)}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(migrate())
