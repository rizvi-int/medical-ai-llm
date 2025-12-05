# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Client Layer                            │
│  (HTTP Requests, curl, Postman, Web Browser, Test Scripts)      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│                     (Port 8000, Docker)                          │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      API Layer                            │  │
│  │  - Health Check (health.py)                               │  │
│  │  - Documents CRUD (documents.py)                          │  │
│  │  - LLM Summarization (llm.py)                             │  │
│  │  - RAG Question Answering (rag.py)                        │  │
│  │  - Agent Extraction (agent.py)                            │  │
│  │  - FHIR Conversion (fhir.py)                              │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                          │                                       │
│  ┌───────────────────────▼──────────────────────────────────┐  │
│  │                   Service Layer                           │  │
│  │  - LLM Service (llm_service.py)                           │  │
│  │  - RAG Service (rag_service.py)                           │  │
│  │  - FHIR Service (fhir_service.py)                         │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                          │                                       │
│  ┌───────────────────────▼──────────────────────────────────┐  │
│  │                    Agent Layer                            │  │
│  │  - Medical Extraction Agent (extraction_agent.py)         │  │
│  │    • Step 1: Extract with LLM                             │  │
│  │    • Step 2: Enrich medications (RxNorm)                  │  │
│  │    • Step 3: Enrich conditions (ICD-10)                   │  │
│  │    • Step 4: Validate & return                            │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │   Qdrant     │  │  External    │
│  Database    │  │   Vector DB  │  │  APIs        │
│  (Port 5432) │  │  (Port 6333) │  │              │
│              │  │              │  │ - NLM RxNorm │
│ - Documents  │  │ - Embeddings │  │ - Clinical   │
│   Table      │  │ - Chunks     │  │   Tables     │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Component Details

### API Layer (FastAPI Routes)

**Responsibility**: Handle HTTP requests, validate input, return responses

```
src/medical_notes_processor/api/
├── health.py          → GET /health
├── documents.py       → GET/POST/DELETE /documents/*
├── llm.py            → POST /summarize_note
├── rag.py            → POST /index_documents, /answer_question
├── agent.py          → POST /extract_structured
└── fhir.py           → POST /to_fhir
```

### Service Layer

**Responsibility**: Business logic, orchestration, external integrations

```
src/medical_notes_processor/services/
├── llm_service.py     → LangChain LLM interactions
├── rag_service.py     → Vector search & retrieval
└── fhir_service.py    → Data transformation to FHIR
```

### Agent Layer

**Responsibility**: Multi-step AI workflows, decision making

```
src/medical_notes_processor/agents/
└── extraction_agent.py → Medical data extraction agent
```

**Agent Workflow**:
```
Input: Raw medical note text
    ↓
┌─────────────────────────────────┐
│ Step 1: LLM Extraction          │
│ Extract structured fields       │
└─────────────┬───────────────────┘
              ↓
┌─────────────────────────────────┐
│ Step 2: Medication Enrichment   │
│ Call NLM RxNorm API             │
│ Add RxNorm codes                │
└─────────────┬───────────────────┘
              ↓
┌─────────────────────────────────┐
│ Step 3: Condition Enrichment    │
│ Call Clinical Tables API        │
│ Add ICD-10 codes                │
└─────────────┬───────────────────┘
              ↓
┌─────────────────────────────────┐
│ Step 4: Validation              │
│ Pydantic model validation       │
│ Return StructuredMedicalData    │
└─────────────────────────────────┘
```

### Data Layer

**Database Models**:
```
src/medical_notes_processor/models/
├── document.py        → SQLAlchemy models
└── schemas.py         → Pydantic schemas
```

**Database**:
```
src/medical_notes_processor/db/
└── base.py            → SQLAlchemy async engine, sessions
```

### Utilities

**External API Clients**:
```
src/medical_notes_processor/utils/
└── external_apis.py   → NLM RxNorm & Clinical Tables clients
```

**Configuration**:
```
src/medical_notes_processor/core/
└── config.py          → Settings, environment variables
```

## Data Flow Examples

### Example 1: Document Creation

```
Client
  ↓ POST /documents {"title": "...", "content": "..."}
API Layer (documents.py)
  ↓ Validate with Pydantic
  ↓ Call database
Database Layer
  ↓ SQLAlchemy async INSERT
PostgreSQL
  ↓ Return created document
API Layer
  ↓ Serialize with Pydantic
Client ← JSON response
```

### Example 2: LLM Summarization

```
Client
  ↓ POST /summarize_note {"text": "..."}
API Layer (llm.py)
  ↓ Validate input
Service Layer (llm_service.py)
  ↓ Prepare prompt
  ↓ Call LangChain
OpenAI API
  ↓ Generate summary
Service Layer
  ↓ Parse response
API Layer
  ↓ Return JSON
Client ← {"summary": "...", "model_used": "..."}
```

### Example 3: RAG Pipeline

```
Client
  ↓ POST /answer_question {"question": "..."}
API Layer (rag.py)
  ↓ Validate
Service Layer (rag_service.py)
  ↓ Generate query embedding
OpenAI Embeddings API
  ↓ Embedding vector
  ↓ Similarity search
Qdrant Vector DB
  ↓ Return top-k chunks
Service Layer
  ↓ Build context from chunks
  ↓ Generate answer with LLM
OpenAI Chat API
  ↓ Answer
Service Layer
  ↓ Add source citations
API Layer
  ↓ Return JSON
Client ← {"answer": "...", "sources": [...]}
```

### Example 4: Agent Extraction

```
Client
  ↓ POST /extract_structured {"text": "..."}
API Layer (agent.py)
  ↓ Validate
Agent Layer (extraction_agent.py)
  ↓ Step 1: Extract with LLM
OpenAI API
  ↓ Raw structured JSON
Agent Layer
  ↓ Step 2: Enrich medications
NLM RxNorm API (parallel requests)
  ↓ RxNorm codes
Agent Layer
  ↓ Step 3: Enrich conditions
Clinical Tables API (parallel requests)
  ↓ ICD-10 codes
Agent Layer
  ↓ Step 4: Validate with Pydantic
  ↓ Return StructuredMedicalData
API Layer
  ↓ Serialize
Client ← {"structured_data": {...}}
```

### Example 5: FHIR Conversion

```
Client
  ↓ POST /to_fhir {"structured_data": {...}}
API Layer (fhir.py)
  ↓ Validate StructuredMedicalData
Service Layer (fhir_service.py)
  ↓ Convert patient → FHIRPatient
  ↓ Convert conditions → FHIRCondition[]
  ↓ Convert medications → FHIRMedication[]
  ↓ Convert vitals → FHIRObservation[]
  ↓ Convert plan → FHIRCarePlan
  ↓ Build FHIRBundle
API Layer
  ↓ Return JSON
Client ← {"fhir_bundle": {...}}
```

## Database Schema

### Documents Table

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_id ON documents(id);
```

## Vector Database Schema (Qdrant)

**Collection**: `medical_documents`

**Vector Config**:
- Size: 1536 (OpenAI ada-002 embedding dimension)
- Distance: Cosine similarity

**Point Metadata**:
```json
{
  "document_id": 1,
  "title": "Medical Note - Case 01",
  "chunk_index": 0
}
```

## External API Integrations

### NLM RxNorm API

**Endpoint**: `https://rxnav.nlm.nih.gov/REST/rxcui.json`

**Purpose**: Get RxNorm codes for medications

**Example Request**:
```
GET https://rxnav.nlm.nih.gov/REST/rxcui.json?name=Metformin
```

**Example Response**:
```json
{
  "idGroup": {
    "rxnormId": ["6809"]
  }
}
```

### NLM Clinical Tables API

**Endpoint**: `https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search`

**Purpose**: Get ICD-10 codes for conditions

**Example Request**:
```
GET https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search?terms=diabetes&sf=code,name&maxList=1
```

**Example Response**:
```json
[3, [...], null, [["E11.9", "Type 2 diabetes mellitus"]]]
```

## Technology Stack

### Application Framework
- **FastAPI**: Async web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation

### Database
- **PostgreSQL 16**: Relational database
- **SQLAlchemy 2.0**: ORM (async)
- **Alembic**: Database migrations

### Vector Database
- **Qdrant**: Vector similarity search

### LLM & AI
- **LangChain**: LLM orchestration
- **LangGraph**: Agent workflows
- **OpenAI**: GPT-4 & embeddings

### Development
- **uv**: Package manager
- **pytest**: Testing framework
- **Docker**: Containerization

## Async Architecture

All I/O operations are asynchronous:

```python
# Database
async with AsyncSession() as session:
    result = await session.execute(query)

# LLM
response = await llm.ainvoke(messages)

# Vector search
docs = await vectorstore.asimilarity_search(query)

# External APIs
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

**Benefits**:
- Non-blocking I/O
- Higher throughput
- Better resource utilization
- Handles concurrent requests efficiently

## Error Handling Strategy

```python
try:
    # Operation
    result = await operation()
except SpecificError as e:
    logger.error(f"Specific error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal error")
```

**Retry Logic** (for external APIs):
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10)
)
async def get_external_data():
    # API call
```

## Scalability Considerations

### Current Architecture
- Single app container
- Single database
- Single vector store

### Production Scaling Options

**Horizontal Scaling**:
```yaml
services:
  app:
    deploy:
      replicas: 3

  # Add load balancer
  nginx:
    image: nginx
    # Load balance across app replicas
```

**Database Scaling**:
- Read replicas for PostgreSQL
- Connection pooling (already implemented)
- Database sharding if needed

**Vector DB Scaling**:
- Qdrant clustering
- Sharded collections

**Caching Layer**:
```yaml
services:
  redis:
    image: redis:alpine
    # Cache LLM responses
    # Cache vector search results
```

## Security Considerations

**Implemented**:
- Environment variable configuration
- No hardcoded credentials
- CORS middleware
- Input validation with Pydantic
- SQL injection prevention (ORM)

**Production Additions Needed**:
- API authentication (JWT)
- Rate limiting
- HTTPS/TLS
- Secrets management (HashiCorp Vault)
- Network policies

## Monitoring & Observability

**Current**:
- Structured logging with levels
- Docker health checks
- Basic error tracking

**Production Additions**:
- Application metrics (Prometheus)
- Distributed tracing (OpenTelemetry)
- Log aggregation (ELK stack)
- Performance monitoring (APM)

## Deployment Architecture

```
Docker Compose (Development)
├── app (FastAPI)
├── db (PostgreSQL)
└── qdrant (Vector DB)

Kubernetes (Production - Future)
├── Ingress (NGINX)
├── FastAPI Deployment (3+ replicas)
├── PostgreSQL StatefulSet
├── Qdrant StatefulSet
└── Redis Deployment (cache)
```

## File Structure by Layer

```
API Layer:
  src/medical_notes_processor/api/*.py

Service Layer:
  src/medical_notes_processor/services/*.py

Agent Layer:
  src/medical_notes_processor/agents/*.py

Data Layer:
  src/medical_notes_processor/models/*.py
  src/medical_notes_processor/db/*.py

Utilities:
  src/medical_notes_processor/utils/*.py
  src/medical_notes_processor/core/*.py

Tests:
  tests/unit/*.py
  tests/integration/*.py

Infrastructure:
  Dockerfile
  docker-compose.yml
  alembic/
```

This architecture provides:
- Separation of concerns
- Easy testing
- Scalability
- Maintainability
- Production readiness
