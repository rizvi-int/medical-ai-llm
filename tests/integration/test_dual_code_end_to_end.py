"""
End-to-end integration test for dual ICD-10 code extraction feature.

Tests the complete flow from medical note → LLM extraction → API validation → formatting.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dual_code_extraction_full_flow(client: AsyncClient):
    """
    Test complete dual code extraction flow:
    1. Submit medical note with routine encounter
    2. Verify LLM assigns AI-inferred codes
    3. Verify API validation (may or may not find codes)
    4. Verify response contains both ai_icd10_code and validated_icd10_code fields
    """
    medical_note = {
        "text": """
        Patient: Jane Smith, DOB 1975-03-15
        Date: 2024-01-15

        Chief Complaint: Annual health examination

        History:
        - Family history of hyperlipidemia (father has high cholesterol)
        - No current complaints

        Vital Signs:
        - Height: 165 cm
        - Weight: 75 kg
        - BMI: 27.5 (Overweight range)
        - BP: 122/78
        - HR: 72

        Physical Exam: Normal

        Assessment:
        1. Annual wellness visit - routine health maintenance
        2. Overweight (BMI 27.5) - recommend dietary counseling
        3. Family history of hyperlipidemia - recommend lipid panel screening

        Plan:
        - Order lipid panel
        - Dietary counseling
        - Follow-up in 12 months for next annual exam
        """
    }

    response = await client.post("/extract_structured", json=medical_note)
    assert response.status_code == 200

    data = response.json()
    structured_data = data.get("structured_data", {})
    conditions = structured_data.get("conditions", [])

    # Should have extracted conditions
    assert len(conditions) >= 2, f"Expected at least 2 conditions, got {len(conditions)}"

    # Check for dual code fields
    for condition in conditions:
        assert "name" in condition
        condition_name = condition["name"].lower()

        # Check if AI code field exists (even if None)
        assert "ai_icd10_code" in condition or "icd10_code" in condition, \
            f"Condition {condition['name']} missing code fields"

        # Verify specific condition codes
        if "wellness" in condition_name or "annual" in condition_name or "exam" in condition_name:
            # Should have AI-assigned Z00.00 code
            ai_code = condition.get("ai_icd10_code")
            assert ai_code is not None, "Annual wellness visit should have AI-assigned code"
            assert ai_code.startswith("Z00"), f"Expected Z00.x code, got {ai_code}"

        elif "overweight" in condition_name:
            # Should have AI-assigned E66 code
            ai_code = condition.get("ai_icd10_code")
            assert ai_code is not None, "Overweight should have AI-assigned code"
            assert ai_code.startswith("E66"), f"Expected E66.x code, got {ai_code}"

        elif "family" in condition_name and "hyperlipidemia" in condition_name:
            # Should have AI-assigned Z83 code
            ai_code = condition.get("ai_icd10_code")
            assert ai_code is not None, "Family history should have AI-assigned code"
            assert ai_code.startswith("Z83"), f"Expected Z83.x code, got {ai_code}"


@pytest.mark.asyncio
async def test_dual_code_with_confirmed_diagnosis(client: AsyncClient):
    """
    Test dual codes with a confirmed diagnosis that API should validate.
    """
    medical_note = {
        "text": """
        Patient: Robert Jones, DOB 1965-08-20

        Chief Complaint: Follow-up for diabetes management

        History: Type 2 Diabetes Mellitus diagnosed 5 years ago

        Medications:
        - Metformin 1000mg BID
        - Lisinopril 10mg daily

        Labs:
        - HbA1c: 7.8%
        - Fasting glucose: 145 mg/dL

        Assessment:
        1. Type 2 Diabetes Mellitus - suboptimally controlled
        2. Hypertension - well controlled on current medication

        Plan:
        - Increase Metformin to 1500mg BID
        - Continue Lisinopril
        - Repeat HbA1c in 3 months
        """
    }

    response = await client.post("/extract_structured", json=medical_note)
    assert response.status_code == 200

    data = response.json()
    conditions = data["structured_data"]["conditions"]

    # Find diabetes condition
    diabetes_condition = None
    for cond in conditions:
        if "diabetes" in cond["name"].lower():
            diabetes_condition = cond
            break

    assert diabetes_condition is not None, "Should extract Type 2 Diabetes condition"

    # Should have AI code
    ai_code = diabetes_condition.get("ai_icd10_code")
    assert ai_code is not None, "Diabetes should have AI code"
    assert ai_code.startswith("E11"), f"Expected E11.x for Type 2 Diabetes, got {ai_code}"

    # API validation might find E11.9 or similar
    validated_code = diabetes_condition.get("validated_icd10_code")
    if validated_code:
        assert validated_code.startswith("E11"), \
            f"Validated code should also be E11.x, got {validated_code}"

    # Check medications have RxNorm codes
    medications = data["structured_data"]["medications"]
    assert len(medications) >= 2, "Should extract both medications"

    for med in medications:
        if "metformin" in med["name"].lower():
            # Should have RxNorm code
            assert "rxnorm_code" in med
            # RxNorm code for Metformin is typically 6809
            rxnorm = med.get("rxnorm_code")
            if rxnorm:
                assert len(rxnorm) > 0, "RxNorm code should not be empty"


@pytest.mark.asyncio
async def test_chatbot_table_format_with_dual_codes(client: AsyncClient):
    """
    Test that chatbot returns table format with dual code columns.
    """
    # First, create a test document
    doc_request = {
        "title": "Test Patient - Wellness Visit",
        "content": """
        Annual wellness visit for healthy adult.
        No complaints. Family history of heart disease.
        Vitals normal.
        """
    }

    doc_response = await client.post("/documents", json=doc_request)
    assert doc_response.status_code == 200
    doc_id = doc_response.json()["id"]

    # Ask chatbot for codes in table format
    chat_request = {
        "message": f"extract icd10 codes from document {doc_id} in a table",
        "session_id": "test_dual_codes"
    }

    chat_response = await client.post("/chat", json=chat_request)
    assert chat_response.status_code == 200

    response_text = chat_response.json()["response"]

    # Should be formatted as markdown table
    assert "|" in response_text, "Response should be a table"
    assert "ICD-10 (AI)" in response_text, "Should have AI code column"
    assert "ICD-10 (Validated)" in response_text, "Should have Validated code column"

    # Table should have header separator
    assert "---" in response_text, "Should have markdown table separator"

    # Should show case number
    assert str(doc_id) in response_text, "Should show document ID in table"


@pytest.mark.asyncio
async def test_chatbot_list_format_with_dual_codes(client: AsyncClient):
    """
    Test that chatbot returns list format (non-table) with dual code sections.
    """
    # Create test document
    doc_request = {
        "title": "Test - Routine Exam",
        "content": """
        Routine annual health exam.
        Patient reports family history of diabetes.
        BMI 26 - slightly overweight.
        """
    }

    doc_response = await client.post("/documents", json=doc_request)
    assert doc_response.status_code == 200
    doc_id = doc_response.json()["id"]

    # Ask for codes WITHOUT table keyword
    chat_request = {
        "message": f"what are the icd10 codes for document {doc_id}",
        "session_id": "test_list_format"
    }

    chat_response = await client.post("/chat", json=chat_request)
    assert chat_response.status_code == 200

    response_text = chat_response.json()["response"]

    # Should have dual code sections
    assert "Diagnoses (AI-Inferred Codes):" in response_text or "AI" in response_text, \
        "Should show AI-inferred codes section"
    assert "Diagnoses (API-Validated Codes):" in response_text or "Validated" in response_text or "API" in response_text, \
        "Should show validated codes section"


@pytest.mark.asyncio
async def test_multi_document_table_format(client: AsyncClient):
    """
    Test table format with multiple documents showing dual codes.
    """
    # Create multiple test documents
    docs = [
        {
            "title": "Patient A - Annual Exam",
            "content": "Annual wellness visit. No issues."
        },
        {
            "title": "Patient B - Diabetes Follow-up",
            "content": "Type 2 Diabetes, well controlled on Metformin."
        }
    ]

    doc_ids = []
    for doc_data in docs:
        response = await client.post("/documents", json=doc_data)
        assert response.status_code == 200
        doc_ids.append(response.json()["id"])

    # Request table for multiple documents
    chat_request = {
        "message": f"give me icd10 codes for documents {doc_ids[0]} and {doc_ids[1]} in a table",
        "session_id": "test_multi_table"
    }

    chat_response = await client.post("/chat", json=chat_request)
    assert chat_response.status_code == 200

    response_text = chat_response.json()["response"]

    # Should be a table
    assert "|" in response_text

    # Should contain both document IDs
    assert str(doc_ids[0]) in response_text
    assert str(doc_ids[1]) in response_text

    # Should have code columns
    assert "ICD-10 (AI)" in response_text
    assert "ICD-10 (Validated)" in response_text

    # Count table rows (should have at least 2 data rows + header + separator)
    lines = response_text.split("\n")
    table_lines = [l for l in lines if "|" in l]
    assert len(table_lines) >= 4, f"Expected at least 4 table lines, got {len(table_lines)}"
