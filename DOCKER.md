# Docker Deployment

## Quick Start

```bash
docker compose up -d
```

Access:
- API: http://localhost:8000
- Streamlit UI: http://localhost:8501
- API Docs: http://localhost:8000/docs
- Qdrant UI: http://localhost:6334

## Services

| Service | Port | Purpose |
|---------|------|---------|
| app | 8000 | FastAPI backend with LLM extraction |
| streamlit | 8501 | Conversational UI |
| qdrant | 6333 | Vector database for RAG |

## Common Commands

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f app

# Restart service
docker compose restart app

# Stop all
docker compose down

# Rebuild and start
docker compose up --build

# Shell into container
docker compose exec app bash
```

## Troubleshooting

**Services won't start:**
```bash
docker compose down
docker compose up --build
```

**Check service status:**
```bash
docker compose ps
```

**View specific service logs:**
```bash
docker compose logs app --tail=100
```

**Reset everything:**
```bash
docker compose down -v  # Warning: deletes data
docker compose up --build
```
