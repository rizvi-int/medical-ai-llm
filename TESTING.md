# Testing Guide

Comprehensive guide for testing all parts of the Medical Notes Processor.

## Prerequisites

1. Services must be running:
   ```bash
   docker-compose up -d
   ```

2. Verify all services are healthy:
   ```bash
   docker-compose ps
   ```

## Automated Test Suite

### Run All Tests
```bash
# Using make
make test

# Or directly
docker-compose exec app pytest -v
```

### Run Specific Test Files
```bash
docker-compose exec app pytest tests/unit/test_health.py -v
docker-compose exec app pytest tests/unit/test_documents.py -v
docker-compose exec app pytest tests/unit/test_fhir_service.py -v
```

### Test with Coverage
```bash
docker-compose exec app pytest --cov=medical_notes_processor --cov-report=html tests/
```

View coverage report: Open `htmlcov/index.html` in your browser

## Manual Testing - All API Endpoints

### Automated Script
Run the comprehensive test script:
```bash
./scripts/test_all_endpoints.sh
```

### Manual Step-by-Step Testing

#### Part 1: FastAPI Backend Foundation

**1. Health Check**
```bash
curl http://localhost:8000/health
```
Expected: `{"status": "ok"}`

**2. Get All Document IDs**
```bash
curl http://localhost:8000/documents
```
Expected: Array of integers `[1, 2, 3, 4, 5, 6]`

**3. Get All Documents**
```bash
curl http://localhost:8000/documents/all | jq .
```
Expected: Array of document objects with id, title, content

**4. Get Specific Document**
```bash
curl http://localhost:8000/documents/1 | jq .
```
Expected: Single document object

**5. Create New Document**
```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Note",
    "content": "S: Test subjective\nO: Test objective\nA: Test assessment\nP: Test plan"
  }' | jq .
```
Expected: Created document with ID

**6. Delete Document**
```bash
curl -X DELETE http://localhost:8000/documents/7
```
Expected: 204 No Content

#### Part 2: LLM API Integration

**Summarize Medical Note**
```bash
curl -X POST http://localhost:8000/summarize_note \
  -H "Content-Type: application/json" \
  -d '{
    "text": "SOAP Note - Encounter Date: 2024-06-15\nPatient: John Doe - DOB 1980-05-15\n\nS:\nPatient reports persistent headache for 3 days, worsening in the morning. No visual changes, no nausea.\n\nO:\nVitals: BP 125/82 mmHg, HR 76 bpm, Temp 98.4F\nNeuro exam: Normal, no focal deficits\nFundoscopic exam: Normal\n\nA:\nTension-type headache\n\nP:\nRecommend OTC ibuprofen 400mg as needed\nStress management techniques\nFollow-up if symptoms worsen or persist beyond 1 week"
  }' | jq .
```

Expected output:
```json
{
  "summary": "Patient presents with persistent headache...",
  "model_used": "gpt-4-turbo-preview"
}
```

#### Part 3: RAG Pipeline

**1. Index Documents**
```bash
curl -X POST http://localhost:8000/index_documents | jq .
```

Expected:
```json
{
  "message": "Successfully indexed 6 documents",
  "document_count": 6
}
```

**2. Ask Questions**

Test with different questions:

```bash
# Question 1: About medications
curl -X POST http://localhost:8000/answer_question \
  -H "Content-Type: application/json" \
  -d '{"question": "What medications were prescribed?"}' | jq .

# Question 2: About physical therapy
curl -X POST http://localhost:8000/answer_question \
  -H "Content-Type: application/json" \
  -d '{"question": "What physical therapy exercises were recommended?"}' | jq .

# Question 3: About vital signs
curl -X POST http://localhost:8000/answer_question \
  -H "Content-Type: application/json" \
  -d '{"question": "What were the patient vital signs?"}' | jq .
```

Expected: Answer with sources citation

#### Part 4: Agent for Structured Data Extraction

**Extract Structured Data**
```bash
curl -X POST http://localhost:8000/extract_structured \
  -H "Content-Type: application/json" \
  -d '{
    "text": "SOAP Note - Encounter Date: 2024-06-15\nPatient: Jane Smith - DOB 1975-08-22\n\nS:\nPatient reports increased thirst, frequent urination, and fatigue for past 3 weeks. No prior diabetes diagnosis. Family history positive for Type 2 DM.\n\nO:\nVitals:\nBP: 138/86 mmHg\nHR: 80 bpm\nWeight: 190 lbs\nHeight: 5 foot 6 inches\n\nLab Results:\nHbA1c: 7.8%\nFasting glucose: 156 mg/dL\nRandom glucose: 215 mg/dL\n\nA:\nType 2 Diabetes Mellitus, newly diagnosed\nPre-hypertension\n\nP:\n1. Start Metformin 500mg twice daily with meals\n2. Dietary consultation for diabetes management\n3. Home blood glucose monitoring\n4. Repeat HbA1c in 3 months\n5. Lifestyle modifications: diet and exercise\n6. Follow-up in 2 weeks"
  }' | jq .
```

Expected output should include:
- Patient information
- Vital signs
- Conditions with ICD-10 codes (e.g., "E11" for Type 2 DM)
- Medications with RxNorm codes (e.g., "6809" for Metformin)
- Lab results
- Plan actions

**Verify Code Enrichment**

The agent should automatically look up:
- **ICD-10 codes** for conditions (Type 2 Diabetes → E11.9)
- **RxNorm codes** for medications (Metformin → 6809)

Check the response contains these fields:
```json
{
  "structured_data": {
    "conditions": [
      {
        "name": "Type 2 Diabetes Mellitus",
        "icd10_code": "E11.9"
      }
    ],
    "medications": [
      {
        "name": "Metformin",
        "rxnorm_code": "6809"
      }
    ]
  }
}
```

#### Part 5: FHIR Conversion

**Convert Structured Data to FHIR**

First extract structured data, then convert:

```bash
# Step 1: Extract
STRUCTURED=$(curl -s -X POST http://localhost:8000/extract_structured \
  -H "Content-Type: application/json" \
  -d '{
    "text": "SOAP Note - Encounter Date: 2024-06-15\nPatient: John Doe - DOB 1980-05-15\nS: Patient with diabetes\nO: BP 130/85\nA: Type 2 Diabetes\nP: Metformin 500mg BID"
  }')

# Step 2: Convert to FHIR
echo $STRUCTURED | curl -X POST http://localhost:8000/to_fhir \
  -H "Content-Type: application/json" \
  -d @- | jq .
```

Expected FHIR Bundle with:
- Patient resource
- Condition resources
- MedicationRequest resources
- Observation resources (vitals)
- CarePlan resource

## Testing Edge Cases

### 1. Invalid Data Validation
```bash
# Empty content
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "content": ""}' | jq .
# Expected: 422 Validation Error

# Missing field
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"title": "Test"}' | jq .
# Expected: 422 Validation Error
```

### 2. Non-existent Resources
```bash
# Non-existent document
curl http://localhost:8000/documents/99999 | jq .
# Expected: 404 Not Found
```

### 3. RAG with No Documents
```bash
# Ask question before indexing (on fresh database)
curl -X POST http://localhost:8000/answer_question \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the treatment?"}' | jq .
# Expected: "No relevant information found"
```

## Integration Testing

### End-to-End Workflow Test

Complete workflow from document creation to FHIR conversion:

```bash
# 1. Create document
DOC_ID=$(curl -s -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Integration Test Note",
    "content": "S: Patient reports symptoms\nO: BP 120/80\nA: Hypertension\nP: Lisinopril 10mg daily"
  }' | jq -r '.id')

echo "Created document ID: $DOC_ID"

# 2. Retrieve document
CONTENT=$(curl -s http://localhost:8000/documents/$DOC_ID | jq -r '.content')

# 3. Summarize
curl -s -X POST http://localhost:8000/summarize_note \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$CONTENT\"}" | jq .

# 4. Extract structured data
STRUCTURED=$(curl -s -X POST http://localhost:8000/extract_structured \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$CONTENT\"}")

# 5. Convert to FHIR
echo $STRUCTURED | curl -s -X POST http://localhost:8000/to_fhir \
  -H "Content-Type: application/json" \
  -d @- | jq .
```

## Performance Testing

### Test LLM Response Time
```bash
time curl -X POST http://localhost:8000/summarize_note \
  -H "Content-Type: application/json" \
  -d '{"text": "S: Test\nO: Test\nA: Test\nP: Test"}'
```

### Test RAG Performance
```bash
# Index documents
time curl -X POST http://localhost:8000/index_documents

# Query
time curl -X POST http://localhost:8000/answer_question \
  -H "Content-Type: application/json" \
  -d '{"question": "What treatments were prescribed?"}'
```

## Troubleshooting Tests

### Check Logs
```bash
# App logs
docker-compose logs app

# Database logs
docker-compose logs db

# Qdrant logs
docker-compose logs qdrant
```

### Verify Service Health
```bash
# PostgreSQL
docker-compose exec db pg_isready

# Qdrant
curl http://localhost:6333/health
```

### Reset Test Environment
```bash
# Stop services
make down

# Clean everything
make clean

# Rebuild and start
make build
make up

# Wait for services to be ready
sleep 10

# Verify
curl http://localhost:8000/health
```

## Expected Test Results Summary

✓ Health check returns 200 OK
✓ Documents CRUD operations work correctly
✓ LLM summarization returns coherent summaries
✓ RAG indexing completes successfully
✓ RAG question answering returns relevant results with sources
✓ Agent extracts structured data with proper schema
✓ Agent enriches medications with RxNorm codes
✓ Agent enriches conditions with ICD-10 codes
✓ FHIR conversion produces valid FHIR resources
✓ All validation errors handled gracefully
✓ All 404 errors for non-existent resources

## Next Steps

- Run `./scripts/test_all_endpoints.sh` for automated testing
- Check the Swagger docs at http://localhost:8000/docs for interactive testing
- Review unit test coverage with `make test`
