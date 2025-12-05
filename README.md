# Medical Notes Processor

AI-powered medical document processing system with LLM integration, RAG pipeline, structured data extraction, and FHIR conversion.

## Features

- FastAPI Backend with async support
- LLM Integration via OpenAI GPT-4
- RAG Pipeline with Qdrant vector database
- Agent-based structured data extraction
- FHIR conversion with medical coding
- PostgreSQL with SQLAlchemy ORM
- Docker Compose deployment
- Comprehensive test suite

## Quick Start

### 1. Add OpenAI API Key

```bash
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=your-key-here
```

### 2. Start Services

```bash
docker-compose build
docker-compose up -d
```

### 3. Verify

```bash
curl http://localhost:8000/health
```

## API Endpoints

### Documents
- `GET /health` - Health check
- `GET /documents` - List all document IDs
- `GET /documents/all` - Get all documents
- `GET /documents/{id}` - Get specific document
- `POST /documents` - Create document
- `DELETE /documents/{id}` - Delete document

### LLM
- `POST /summarize_note` - Summarize medical note

### RAG
- `POST /index_documents` - Index documents for search
- `POST /answer_question` - Answer questions using RAG

### Agent
- `POST /extract_structured` - Extract structured data with medical codes

### FHIR
- `POST /to_fhir` - Convert to FHIR format

### Chatbot
- `POST /chat` - Linear RAG pipeline chatbot with context-aware answers

## Testing

```bash
# Run all tests
make test

# Run automated endpoint tests
./scripts/test_all_endpoints.sh
```

## Tech Stack

- FastAPI + Uvicorn
- PostgreSQL 16
- Qdrant (vector DB)
- LangChain + LangGraph
- SQLAlchemy 2.0 (async)
- pytest
- Docker Compose

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - 5-minute setup guide
- [TESTING.md](TESTING.md) - Comprehensive testing guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Feature overview
- [DATABASE_SEEDING.md](DATABASE_SEEDING.md) - Automatic seeding with 14 SOAP notes
- [CHATBOT_REFACTORING.md](CHATBOT_REFACTORING.md) - Linear RAG pipeline architecture
- [ROADMAP_V1_V2.md](ROADMAP_V1_V2.md) - Implementation details and extension proposals
- [REQUIREMENTS_CHECKLIST.md](REQUIREMENTS_CHECKLIST.md) - Detailed requirements verification

## Development

```bash
# Local development without Docker
make dev-install
make dev-run

# Run tests locally
make dev-test
```

## Service URLs

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Qdrant: http://localhost:6333/dashboard

## License

MIT
