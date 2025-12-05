# Database Seeding

## Overview

The application automatically seeds both the SQL database and Qdrant vector store with 14 diverse SOAP notes on first startup.

## Seeding Behavior

### Trigger Condition
Seeding occurs automatically when:
- Application starts via `docker-compose up`
- SQL database is empty (document count = 0)

### Data Source
Location: `example_notes/soap_01.txt` through `soap_14.txt`

The glob pattern `soap_*.txt` automatically includes all SOAP files in the directory.

### Two-Phase Process

**Phase 1: SQL Database**
- All 14 SOAP notes inserted into PostgreSQL `documents` table
- Each document assigned sequential ID, title, content, and timestamp
- Title format: `Medical Note - Case 01` through `Case 14`

**Phase 2: Qdrant Vector Store**
- After SQL commit, documents are retrieved and indexed
- Content split into chunks (1000 chars, 200 char overlap)
- Embeddings generated via OpenAI API (model: text-embedding-ada-002)
- Vectors stored in Qdrant collection `medical_notes`
- Metadata preserved: document_id, title, chunk_index

### Error Handling

**SQL Phase**: Failure stops seeding, error logged
**Qdrant Phase**: Failure logged as warning, does not stop application startup

This allows the application to run even if Qdrant is unavailable. Documents can be manually indexed later via `POST /index_documents`.

## SOAP Note Diversity

The 14 notes cover:

1. **Case 01-06**: Original cases (general practice, chronic disease)
2. **Case 07**: Cardiology - STEMI/cardiac catheterization
3. **Case 08**: Pediatrics - Well-child visit with immunizations
4. **Case 09**: Obstetrics - High-risk pregnancy (gestational diabetes)
5. **Case 10**: Geriatrics - Polypharmacy and fall risk
6. **Case 11**: Psychiatry - ADHD and anxiety disorder
7. **Case 12**: Endocrinology - Complex diabetes with complications
8. **Case 13**: Urgent Care - Infectious mononucleosis
9. **Case 14**: Orthopedics - Post-operative ACL reconstruction

## Manual Indexing

If Qdrant indexing fails during startup or documents are added manually:

```bash
curl -X POST http://localhost:8000/index_documents
```

This endpoint:
- Retrieves all documents from SQL database
- Generates embeddings and indexes to Qdrant
- Returns document count confirmation

## Verification

Check seeding status:

```bash
# SQL database
curl http://localhost:8000/documents

# Qdrant indexing (via RAG query)
curl -X POST http://localhost:8000/answer_question \
  -H "Content-Type: application/json" \
  -d '{"question": "What patients do you have records for?"}'
```

Expected: 14 documents in SQL, successful RAG responses indicate Qdrant indexing.

## Implementation

File: `src/medical_notes_processor/main.py`
Function: `lifespan()` (lines 18-73)

The lifespan context manager handles:
- Database initialization
- Automatic seeding on empty database
- Graceful shutdown
