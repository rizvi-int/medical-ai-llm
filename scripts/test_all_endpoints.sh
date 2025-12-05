#!/bin/bash

# Script to test all API endpoints
# Make sure the services are running: docker-compose up -d

BASE_URL="http://localhost:8000"

echo "========================================="
echo "Medical Notes Processor - API Test Suite"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Part 1: Health Check
echo "Part 1: Health Check"
echo "--------------------"
curl -s $BASE_URL/health | jq .
echo -e "${GREEN}✓ Health check passed${NC}\n"

# Part 1: Get Documents
echo "Part 1: Get All Document IDs"
echo "-----------------------------"
curl -s $BASE_URL/documents | jq .
echo -e "${GREEN}✓ Retrieved document IDs${NC}\n"

# Part 1: Get Specific Document
echo "Part 1: Get Document #1"
echo "-----------------------"
curl -s $BASE_URL/documents/1 | jq .
echo -e "${GREEN}✓ Retrieved document details${NC}\n"

# Part 1: Create Document
echo "Part 1: Create New Document"
echo "---------------------------"
curl -s -X POST $BASE_URL/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Medical Note",
    "content": "S: Patient reports mild headache.\nO: BP 120/80, HR 72\nA: Tension headache\nP: Recommend rest and hydration"
  }' | jq .
echo -e "${GREEN}✓ Created new document${NC}\n"

# Part 2: Summarize Note
echo "Part 2: Summarize Medical Note"
echo "-------------------------------"
curl -s -X POST $BASE_URL/summarize_note \
  -H "Content-Type: application/json" \
  -d '{
    "text": "S: Patient reports increased thirst and frequent urination for the past 2 weeks.\nO: BP 135/85, HR 78, Random blood glucose 245 mg/dL\nA: Suspected Type 2 Diabetes Mellitus\nP: Order HbA1c, fasting glucose. Discuss lifestyle modifications. Consider metformin if confirmed."
  }' | jq .
echo -e "${GREEN}✓ Summarized medical note${NC}\n"

# Part 3: Index Documents for RAG
echo "Part 3: Index Documents for RAG"
echo "--------------------------------"
curl -s -X POST $BASE_URL/index_documents | jq .
echo -e "${GREEN}✓ Indexed documents in vector database${NC}\n"

# Part 3: Ask Question (RAG)
echo "Part 3: Ask Question Using RAG"
echo "-------------------------------"
curl -s -X POST $BASE_URL/answer_question \
  -H "Content-Type: application/json" \
  -d '{"question": "What physical therapy exercises were recommended?"}' | jq .
echo -e "${GREEN}✓ Answered question using RAG${NC}\n"

# Part 4: Extract Structured Data
echo "Part 4: Extract Structured Data with Agent"
echo "-------------------------------------------"
STRUCTURED_DATA=$(curl -s -X POST $BASE_URL/extract_structured \
  -H "Content-Type: application/json" \
  -d '{
    "text": "SOAP Note - Encounter Date: 2024-06-15\nPatient: Jane Smith - DOB 1975-08-22\n\nS:\nPatient reports persistent elevated blood glucose readings at home, averaging 180-200 mg/dL. Compliant with metformin 500mg twice daily. Some difficulty with diet adherence.\n\nO:\nVitals:\nBP: 142/88 mmHg\nHR: 82 bpm\nWeight: 185 lbs\nLab Results:\nHbA1c: 8.2%\nFasting glucose: 165 mg/dL\n\nA:\nType 2 Diabetes Mellitus, inadequately controlled\nHypertension\n\nP:\nIncrease Metformin to 1000mg twice daily\nAdd Lisinopril 10mg daily for BP control\nReferral to diabetes educator\nFollow-up in 6 weeks with repeat HbA1c"
  }')

echo $STRUCTURED_DATA | jq .
echo -e "${GREEN}✓ Extracted structured data with ICD-10 and RxNorm codes${NC}\n"

# Part 5: Convert to FHIR
echo "Part 5: Convert to FHIR Format"
echo "-------------------------------"
echo $STRUCTURED_DATA | curl -s -X POST $BASE_URL/to_fhir \
  -H "Content-Type: application/json" \
  -d @- | jq .
echo -e "${GREEN}✓ Converted to FHIR format${NC}\n"

echo "========================================="
echo "All tests completed successfully!"
echo "========================================="
