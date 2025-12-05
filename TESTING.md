# Testing

## Run Tests

```bash
# All tests
uv run pytest tests/ -v

# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests (requires running services)
uv run pytest tests/integration/ -v

# Specific test file
uv run pytest tests/unit/test_dual_code_extraction.py -v

# With coverage
uv run pytest tests/ --cov=src --cov-report=html
```

## Test Organization

```
tests/
├── unit/                          # Fast, isolated tests
│   ├── test_dual_code_extraction.py    # Dual code feature
│   ├── test_chatbot_features.py        # Chatbot logic
│   └── test_table_formatting.py        # Output formatting
│
└── integration/                   # End-to-end tests
    └── test_dual_code_end_to_end.py    # Full workflow
```

## Key Test Suites

### Dual Code Extraction
Tests AI-inferred vs API-validated code scenarios:
```bash
uv run pytest tests/unit/test_dual_code_extraction.py -v
```

### Chatbot Features
Tests multi-document queries, context detection, format handling:
```bash
uv run pytest tests/unit/test_chatbot_features.py -v
```

### Table Formatting
Tests table structure, edge cases, CSV export:
```bash
uv run pytest tests/unit/test_table_formatting.py -v
```

### End-to-End
Tests complete workflow from note to formatted output:
```bash
uv run pytest tests/integration/test_dual_code_end_to_end.py -v
```

## Manual Testing

### Chat API
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "codes for doc 1, 2, 3", "session_id": "test123"}'
```

### FHIR Conversion
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "convert document 1 to fhir", "session_id": "test123"}'
```

### Vital Signs
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "show vital signs from document 4", "session_id": "test123"}'
```

## Performance Testing

Test extraction caching:
```bash
python test_cache_performance.py
```

Expected results:
- First extraction: ~50s
- Format changes: <1s (cached)
