# Docker Deployment Guide

## Quick Start

Run the entire stack with one command:

```bash
docker-compose up --build
```

This will start:
- **FastAPI Backend** on http://localhost:8000
- **Streamlit Frontend** on http://localhost:8501
- **Qdrant Vector Database** on http://localhost:6333

## Services

### 1. FastAPI API (`app`)
- **Port**: 8000
- **Health**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **Features**:
  - Medical notes processing
  - ICD-10/RxNorm code extraction
  - Document summarization
  - RAG-powered Q&A
  - Conversation memory

### 2. Streamlit Frontend (`streamlit`)
- **Port**: 8501
- **URL**: http://localhost:8501
- **Features**:
  - Chat interface for medical notes
  - Auto-detect document IDs
  - Extract codes from multiple patients
  - Summarize medical notes

### 3. Qdrant Vector Database (`qdrant`)
- **API Port**: 6333
- **Web UI**: http://localhost:6334
- **Purpose**: Vector embeddings for RAG search

## Commands

### Start all services
```bash
docker-compose up
```

### Start in background (detached)
```bash
docker-compose up -d
```

### Rebuild and start
```bash
docker-compose up --build
```

### Stop all services
```bash
docker-compose down
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f streamlit
```

### Restart a service
```bash
docker-compose restart app
docker-compose restart streamlit
```

## Environment Variables

Create a `.env` file in the project root:

```env
# OpenAI API
OPENAI_API_KEY=your-openai-api-key-here

# Database (handled by docker-compose)
DATABASE_URL=sqlite:///./data/medical_notes.db

# Qdrant (handled by docker-compose)
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

## Development Mode

The docker-compose.yml includes volume mounts for hot-reloading:

- **Backend**: Changes to `src/` auto-reload
- **Frontend**: Changes to `streamlit_app.py` auto-reload

## Production Deployment

For production, modify `docker-compose.yml`:

1. Remove volume mounts
2. Remove `--reload` flag from uvicorn
3. Add proper secrets management
4. Configure reverse proxy (nginx)
5. Enable HTTPS

Example production command:
```yaml
command: uvicorn src.medical_notes_processor.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Troubleshooting

### Port already in use
```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Host:Container
```

### Reset everything
```bash
docker-compose down -v  # Remove volumes
docker-compose up --build
```

### Access container shell
```bash
docker exec -it medical-notes-app bash
docker exec -it medical-notes-streamlit bash
```

## Architecture

```
┌─────────────────┐
│   Streamlit UI  │ :8501
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI App   │ :8000
└────────┬────────┘
         │
         ├────────► Qdrant (Vector DB) :6333
         └────────► SQLite (Documents)
```

## Chatbot Features

The containerized chatbot includes:

✅ **Fast responses** - optimized hybrid architecture
✅ **Conversation memory** - remembers context
✅ **Auto-detection** - finds document IDs automatically
✅ **Parallel processing** - extracts codes from all patients simultaneously
✅ **Smart routing** - detects when to summarize vs extract codes

## Example Queries

Try these in the Streamlit UI:

- "What medical documents do you have?"
- "Summarize document 1"
- "Extract ICD-10 codes for all patients"
- "What medications are in document 2 and 3?"
- "Show me diagnoses for patient 4"

## Health Checks

All services include health checks:

```bash
# FastAPI
curl http://localhost:8000/health

# Streamlit
curl http://localhost:8501/_stcore/health

# Qdrant
curl http://localhost:6333/health
```

## Data Persistence

Data is persisted in Docker volumes:

- `qdrant_data`: Vector embeddings
- `./data`: SQLite database (via bind mount)

To backup:
```bash
docker-compose down
tar -czf backup.tar.gz data/
```
