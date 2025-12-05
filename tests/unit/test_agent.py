import pytest
from httpx import AsyncClient
import os


# These tests require a valid OpenAI API key
# Skip if using placeholder key
pytestmark = pytest.mark.skipif(
    os.getenv("OPENAI_API_KEY", "").startswith("your-") or not os.getenv("OPENAI_API_KEY"),
    reason="OpenAI API key not configured - skipping agent extraction tests"
)


@pytest.mark.asyncio
async def test_extract_structured_success(client: AsyncClient):
    """Test successful structured data extraction."""
    note_data = {
        "text": """
        Patient: John Doe, DOB 1980-05-15
        Diagnosis: Type 2 Diabetes
        Medication: Metformin 500mg twice daily
        Vitals: BP 130/85, HR 78
        """
    }

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 200

    data = response.json()
    assert "structured_data" in data
    structured = data["structured_data"]
    assert "patient" in structured
    assert "conditions" in structured
    assert "medications" in structured
    assert "vital_signs" in structured


@pytest.mark.asyncio
async def test_extract_empty_note(client: AsyncClient):
    """Test extraction with empty medical note."""
    note_data = {"text": ""}

    response = await client.post("/extract_structured", json=note_data)
    # Pydantic validation requires non-empty string
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_extract_missing_text(client: AsyncClient):
    """Test extraction without text field."""
    note_data = {}

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_extract_whitespace_only(client: AsyncClient):
    """Test extraction with only whitespace."""
    note_data = {"text": "   \n\n\t   "}

    response = await client.post("/extract_structured", json=note_data)
    # Should still process (LLM can handle whitespace)
    assert response.status_code in [200, 422]


@pytest.mark.asyncio
async def test_extract_minimal_data(client: AsyncClient):
    """Test extraction with minimal medical information."""
    note_data = {"text": "Patient presents with cough."}

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 200

    data = response.json()
    assert "structured_data" in data


@pytest.mark.asyncio
async def test_extract_complex_medications(client: AsyncClient):
    """Test extraction with complex medication regimens."""
    note_data = {
        "text": """
        Medications:
        1. Metformin 1000mg PO BID with meals
        2. Lisinopril 10mg PO daily in AM
        3. Atorvastatin 40mg PO qHS
        4. Aspirin 81mg PO daily
        5. Insulin glargine 20 units SC qHS
        """
    }

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 200

    data = response.json()
    structured = data["structured_data"]
    # Should extract at least some medications
    assert "medications" in structured


@pytest.mark.asyncio
async def test_extract_multiple_conditions(client: AsyncClient):
    """Test extraction with multiple chronic conditions."""
    note_data = {
        "text": """
        Problem List:
        1. Type 2 Diabetes Mellitus, uncontrolled
        2. Hypertension
        3. Hyperlipidemia
        4. Chronic Kidney Disease Stage 3
        5. Obesity (BMI 32)
        """
    }

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 200

    data = response.json()
    structured = data["structured_data"]
    assert "conditions" in structured


@pytest.mark.asyncio
async def test_extract_incomplete_vitals(client: AsyncClient):
    """Test extraction with partial vital signs."""
    note_data = {
        "text": "Vitals: BP 140/90, patient refused weight"
    }

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 200

    data = response.json()
    structured = data["structured_data"]
    assert "vital_signs" in structured


@pytest.mark.asyncio
async def test_extract_abnormal_vitals(client: AsyncClient):
    """Test extraction with abnormal vital signs."""
    note_data = {
        "text": "Vitals: BP 180/110, HR 110, Temp 101.5F, O2 sat 88% on RA"
    }

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_pediatric_data(client: AsyncClient):
    """Test extraction with pediatric-specific data."""
    note_data = {
        "text": """
        Patient: Emma Smith, DOB 2019-01-15 (5 years old)
        Weight: 18kg (55th percentile)
        Height: 110cm (50th percentile)
        Immunizations: DTaP, IPV, MMR, Varicella administered today
        """
    }

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_lab_results(client: AsyncClient):
    """Test extraction with laboratory results."""
    note_data = {
        "text": """
        Labs:
        - Hemoglobin A1c: 8.2% (elevated)
        - Creatinine: 1.3 mg/dL
        - eGFR: 55 mL/min/1.73m²
        - LDL: 150 mg/dL
        - Triglycerides: 200 mg/dL
        """
    }

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_null_text(client: AsyncClient):
    """Test extraction with null text value."""
    note_data = {"text": None}

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_extract_non_english_text(client: AsyncClient):
    """Test extraction with non-English medical note."""
    note_data = {
        "text": "Paciente: María González\nDiagnóstico: Diabetes tipo 2\nMedicamento: Metformina 500mg"
    }

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_extremely_long_note(client: AsyncClient):
    """Test extraction with very long medical note."""
    long_history = "Patient has extensive medical history. " * 200  # Reduced for speed
    note_data = {"text": long_history}

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_special_medical_symbols(client: AsyncClient):
    """Test extraction with special medical symbols."""
    note_data = {
        "text": "Patient c/o ↑ BP & ♂ pattern baldness. Rx: ↓ Na+ intake, ↑ exercise"
    }

    response = await client.post("/extract_structured", json=note_data)
    assert response.status_code == 200
