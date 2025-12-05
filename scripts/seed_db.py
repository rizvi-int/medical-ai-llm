import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy.ext.asyncio import AsyncSession
from medical_notes_processor.db.base import AsyncSessionLocal
from medical_notes_processor.models.document import Document


async def seed_documents():
    """Seed database with example SOAP notes."""
    example_notes_dir = Path(__file__).resolve().parent.parent / "example_notes"

    if not example_notes_dir.exists():
        print(f"Error: {example_notes_dir} not found")
        return

    soap_files = sorted(example_notes_dir.glob("soap_*.txt"))

    if not soap_files:
        print("No SOAP note files found")
        return

    async with AsyncSessionLocal() as session:
        # Check if documents already exist
        from sqlalchemy import select, func
        result = await session.execute(select(func.count(Document.id)))
        count = result.scalar()

        if count > 0:
            print(f"Database already has {count} documents. Skipping seed.")
            return

        # Add documents
        for soap_file in soap_files:
            content = soap_file.read_text()
            title = f"Medical Note - {soap_file.stem.replace('soap_', 'Case ')}"

            document = Document(title=title, content=content)
            session.add(document)
            print(f"Added: {title}")

        await session.commit()
        print(f"\nSuccessfully seeded {len(soap_files)} documents")


if __name__ == "__main__":
    asyncio.run(seed_documents())
