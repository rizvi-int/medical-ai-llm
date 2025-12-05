# Medical Notes Processor

AI-powered medical document processing with LLM extraction, ICD-10/RxNorm coding, FHIR conversion, and conversational interface.

## Quick Start

```bash
# 1. Add OpenAI API key
cp .env.example .env
# Edit .env: OPENAI_API_KEY=your-key-here

# 2. Start services
docker compose up -d

# 3. Access
# API: http://localhost:8000
# Streamlit UI: http://localhost:8501
# API Docs: http://localhost:8000/docs
```

## Core Features

### 1. Intelligent Code Extraction
- **Dual ICD-10 Codes**: AI-inferred codes + API-validated codes for transparency
- **Confidence Scoring**: HIGH/MEDIUM/LOW confidence with reasoning for each code
- **RxNorm Medications**: Automatic medication code lookup
- **Smart Inference**: Assigns codes for encounters, family history, and observations

### 2. Conversational Chatbot
- **Multi-document queries**: "show codes for doc 1, 2, and 3"
- **Context awareness**: "export to csv" remembers previous documents
- **Multiple formats**: Table, CSV, detailed list with reasoning
- **Extraction caching**: Instant format changes after initial extraction
- **CSV downloads**: Direct download button in Streamlit UI

### 3. Additional Capabilities
- **FHIR Conversion**: "convert document 1 to fhir format"
- **Vital Signs**: "show me vital signs from document 4"
- **Summarization**: "summarize document 2"
- **RAG Search**: Ask questions about all documents

## Architecture

```
FastAPI Backend (Port 8000)
├── LLM Integration (OpenAI GPT-4)
├── Agent-based Extraction
│   ├── Medical coding with confidence
│   ├── RxNorm/ICD-10 enrichment
│   └── Session-based caching
├── RAG Pipeline (Qdrant vector DB)
├── PostgreSQL Database
└── FHIR Converter

Streamlit UI (Port 8501)
└── Conversational interface with CSV downloads
```

## API Endpoints

### Chat
- `POST /chat` - Conversational interface with memory
  - Request: `{"message": "codes for doc 1", "session_id": "abc123"}`
  - Supports: code extraction, FHIR, vitals, summarization, RAG

### Documents
- `GET /documents` - List all documents
- `GET /documents/{id}` - Get specific document
- `POST /documents` - Create document
- `DELETE /documents/{id}` - Delete document

### Extraction
- `POST /extract_structured` - Extract structured medical data
  - Returns: patient info, diagnoses with dual codes + confidence, medications, vitals, labs, plan

### FHIR
- `POST /to_fhir` - Convert structured data to FHIR bundle

### RAG
- `POST /ask` - Ask questions about documents using RAG

## Usage Examples

### Chatbot Interface (Recommended)

```bash
# Via API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what are the icd10 codes for doc 1 and 2?", "session_id": "user123"}'

# Response: Table with dual codes and confidence scores

# Follow-up (uses cached extraction)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "export to csv", "session_id": "user123"}'
```

### Supported Queries

**Code Extraction:**
- "what are the icd10 codes for doc 1, 2, and 3?"
- "show codes for patient 5"
- "give me codes in a table"
- "export to csv"
- "show detailed list with reasoning"

**FHIR Conversion:**
- "convert document 1 to fhir format"

**Vital Signs:**
- "show me vital signs from document 4"

**Summarization:**
- "summarize document 2"

**General Questions:**
- "which patients have diabetes?"
- "show me all medications prescribed"

## Data Model

### Condition (Diagnosis)
```python
{
  "name": "Annual health examination",
  "status": "active",
  "ai_icd10_code": "Z00.00",              # AI-inferred code
  "validated_icd10_code": null,            # API-validated code
  "confidence": "high",                    # HIGH/MEDIUM/LOW
  "code_reasoning": "Routine wellness visit"
}
```

### Output Formats

**Table Format:**
| Case | Document | Diagnosis | ICD-10 (AI) | Confidence | ICD-10 (Validated) |
|------|----------|-----------|-------------|------------|--------------------|
| 1    | Case 01  | Wellness  | Z00.00      | HIGH       | N/A                |

**CSV Format:**
```csv
Case,Document Title,Diagnosis,ICD-10 (AI),Confidence,ICD-10 (Validated),Medication,RxNorm,Code Reasoning
1,Case 01,Wellness,Z00.00,HIGH,N/A,-,-,Routine wellness visit
```

**Detailed List:**
```
Extracted from: Medical Note - Case 01

Diagnoses (AI-Inferred Codes):
  - Annual health examination (ICD-10: Z00.00) [HIGH]
    → Routine wellness visit explicitly documented

Medications:
  - Atorvastatin 20mg (RxNorm: 617318)
```

## Performance

### Extraction Caching
- **First request**: ~50s (extraction + caching)
- **Format changes**: <1s (uses cache)
- **Result**: 4x faster for multi-format workflows

### Parallel Processing
- Bulk extraction uses parallel processing for speed
- Session-based caching persists across requests

## Testing

```bash
# Unit tests
uv run pytest tests/unit/ -v

# Integration tests (requires running services)
uv run pytest tests/integration/ -v

# Specific test suites
uv run pytest tests/unit/test_dual_code_extraction.py -v
uv run pytest tests/unit/test_chatbot_features.py -v
```

## Development

### Project Structure
```
src/medical_notes_processor/
├── api/              # FastAPI endpoints
├── agents/           # Extraction agent with confidence scoring
├── models/           # Pydantic schemas
├── services/         # Business logic (chatbot, FHIR, RAG)
├── utils/            # External API clients (RxNorm, ICD-10)
└── core/             # Config, database

tests/
├── unit/             # Unit tests
└── integration/      # End-to-end tests

streamlit_app.py      # Streamlit UI
```

### Configuration

Environment variables in `.env`:
```bash
# Required
OPENAI_API_KEY=your-key-here

# Optional (defaults shown)
OPENAI_MODEL=gpt-4o
DATABASE_URL=postgresql://user:pass@db:5432/medical_notes
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

## Key Implementations

### Dual Code System
- **AI Code**: LLM assigns clinically appropriate codes using reasoning
- **Validated Code**: Clinical Tables API confirms code exists in database
- **Benefit**: Captures Z codes, family history, observations that APIs miss

### Confidence Scoring
- **HIGH**: Explicitly documented diagnosis
- **MEDIUM**: Inferred from context, symptoms, or medications
- **LOW**: Uncertain or ambiguous

### Smart Features
- **Context Detection**: Recognizes "export to csv" refers to previous documents
- **Format Auto-selection**: Table for multiple docs, list for single doc
- **Session Management**: UUID-based sessions with conversation memory
- **Cache Management**: Automatic cleanup on session reset

## Troubleshooting

**Services not starting:**
```bash
docker compose down
docker compose up --build
```

**OpenAI API errors:**
- Check `.env` has valid `OPENAI_API_KEY`
- Verify API quota/billing

**Database issues:**
```bash
docker compose exec db psql -U user -d medical_notes
# Check tables exist
```

**Clear cache/sessions:**
```bash
curl -X POST http://localhost:8000/chat/reset?session_id=your-session-id
```

## Documentation

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Docker Setup**: See `DOCKER.md`
- **Testing Guide**: See `TESTING.md`

## Tech Stack

- **Backend**: FastAPI, Python 3.11, asyncio
- **AI**: OpenAI GPT-4, LangChain
- **Database**: PostgreSQL, SQLAlchemy
- **Vector DB**: Qdrant
- **UI**: Streamlit
- **Deployment**: Docker Compose
- **Testing**: pytest, httpx

## License

Proprietary
