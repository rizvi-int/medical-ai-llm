# Quick Start Guide

Get the Medical Notes Processor up and running in 5 minutes.

## Step 1: Add Your OpenAI API Key

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env  # or use your favorite editor
```

Replace `your-api-key-here` with your actual OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

## Step 2: Start the Services

```bash
# Build Docker images
docker-compose build

# Start all services (app, PostgreSQL, Qdrant)
docker-compose up -d
```

Wait about 30 seconds for services to fully start.

## Step 3: Verify It's Working

```bash
# Check health
curl http://localhost:8000/health

# You should see: {"status":"ok"}
```

## Step 4: Try the API

### Get the seeded documents
```bash
curl http://localhost:8000/documents
# Returns: [1, 2, 3, 4, 5, 6]
```

### Summarize a medical note
```bash
curl -X POST http://localhost:8000/summarize_note \
  -H "Content-Type: application/json" \
  -d '{"text": "S: Patient reports headache.\nO: BP 120/80\nA: Tension headache\nP: Rest and hydration"}'
```

### Extract structured data with medical codes
```bash
curl -X POST http://localhost:8000/extract_structured \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient: John Doe, DOB 1980-05-15\nDiagnosis: Type 2 Diabetes\nMedication: Metformin 500mg twice daily\nVitals: BP 130/85, HR 78"
  }'
```

## Step 5: Explore the Interactive Docs

Open your browser to:
- **API Docs**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Complete Example Workflow

```bash
# 1. Index documents for RAG
curl -X POST http://localhost:8000/index_documents

# 2. Ask a question
curl -X POST http://localhost:8000/answer_question \
  -H "Content-Type: application/json" \
  -d '{"question": "What physical therapy exercises were recommended?"}'
```

## Run the Automated Test Suite

```bash
# Run all unit and integration tests
docker-compose exec app pytest -v

# Or use make
make test
```

## View Logs

```bash
# All services
docker-compose logs -f

# Just the app
docker-compose logs -f app
```

## Stop Services

```bash
docker-compose down
```

## Troubleshooting

**Services won't start?**
```bash
docker-compose logs
```

**Database connection errors?**
```bash
# Check if PostgreSQL is ready
docker-compose exec db pg_isready
```

**Qdrant not responding?**
```bash
curl http://localhost:6333/health
```

**API key not working?**
- Make sure you updated `.env` (not `.env.example`)
- Restart services: `docker-compose down && docker-compose up -d`

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [TESTING.md](TESTING.md) for comprehensive testing guide
- Run `./scripts/test_all_endpoints.sh` for automated API testing
- Review [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for architecture details

## What's Running?

| Service | Port | URL |
|---------|------|-----|
| FastAPI App | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| PostgreSQL | 5432 | localhost:5432 |
| Qdrant | 6333 | http://localhost:6333 |

## Development Mode

```bash
# For local development without Docker
make dev-install
make dev-run
```

System is now operational and ready for medical document processing.
