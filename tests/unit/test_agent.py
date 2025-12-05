import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


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

    with patch('medical_notes_processor.agents.extraction_agent.extract_structured_data') as mock_extract:
        mock_extract.return_value = {
            "patient": {"name": "John Doe", "date_of_birth": "1980-05-15"},
            "conditions": [{"name": "Type 2 Diabetes", "icd10_code": "E11.9"}],
            "medications": [{"name": "Metformin", "dosage": "500mg", "rxnorm_code": "6809"}],
            "vital_signs": {"blood_pressure": "130/85 mmHg", "heart_rate": "78 bpm"}
        }

        response = await client.post("/extract_structured", json=note_data)
        assert response.status_code == 200

        data = response.json()
        assert "patient" in data
        assert "conditions" in data
        assert "medications" in data


@pytest.mark.asyncio
async def test_extract_empty_note(client: AsyncClient):
    """Test extraction with empty medical note."""
    note_data = {"text": ""}

    response = await client.post("/extract_structured", json=note_data)
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
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_extract_minimal_data(client: AsyncClient):
    """Test extraction with minimal medical information."""
    note_data = {"text": "Patient presents with cough."}

    with patch('medical_notes_processor.agents.extraction_agent.extract_structured_data') as mock_extract:
        mock_extract.return_value = {
            "patient": None,
            "conditions": [],
            "medications": [],
            "vital_signs": None,
            "assessment": "Cough",
            "plan_actions": []
        }

        response = await client.post("/extract_structured", json=note_data)
        assert response.status_code == 200


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

    with patch('medical_notes_processor.agents.extraction_agent.extract_structured_data') as mock_extract:
        mock_extract.return_value = {
            "medications": [
                {"name": "Metformin", "dosage": "1000mg", "frequency": "twice daily", "route": "oral"},
                {"name": "Lisinopril", "dosage": "10mg", "frequency": "daily", "route": "oral"},
                {"name": "Atorvastatin", "dosage": "40mg", "frequency": "nightly", "route": "oral"},
                {"name": "Aspirin", "dosage": "81mg", "frequency": "daily", "route": "oral"},
                {"name": "Insulin glargine", "dosage": "20 units", "frequency": "nightly", "route": "subcutaneous"}
            ]
        }

        response = await client.post("/extract_structured", json=note_data)
        assert response.status_code == 200
        data = response.json()
        assert len(data.get("medications", [])) >= 5


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

    with patch('medical_notes_processor.agents.extraction_agent.extract_structured_data') as mock_extract:
        mock_extract.return_value = {
            "conditions": [
                {"name": "Type 2 Diabetes Mellitus", "status": "active", "icd10_code": "E11.9"},
                {"name": "Hypertension", "status": "active", "icd10_code": "I10"},
                {"name": "Hyperlipidemia", "status": "active", "icd10_code": "E78.5"},
                {"name": "Chronic Kidney Disease Stage 3", "status": "active"},
                {"name": "Obesity", "status": "active"}
            ]
        }

        response = await client.post("/extract_structured", json=note_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_incomplete_vitals(client: AsyncClient):
    """Test extraction with partial vital signs."""
    note_data = {
        "text": "Vitals: BP 140/90, patient refused weight"
    }

    with patch('medical_notes_processor.agents.extraction_agent.extract_structured_data') as mock_extract:
        mock_extract.return_value = {
            "vital_signs": {
                "blood_pressure": "140/90 mmHg",
                "heart_rate": None,
                "temperature": None,
                "weight": None
            }
        }

        response = await client.post("/extract_structured", json=note_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_abnormal_vitals(client: AsyncClient):
    """Test extraction with abnormal vital signs."""
    note_data = {
        "text": "Vitals: BP 180/110, HR 110, Temp 101.5F, O2 sat 88% on RA"
    }

    with patch('medical_notes_processor.agents.extraction_agent.extract_structured_data') as mock_extract:
        mock_extract.return_value = {
            "vital_signs": {
                "blood_pressure": "180/110 mmHg",
                "heart_rate": "110 bpm",
                "temperature": "101.5 F",
                "oxygen_saturation": "88% on room air"
            }
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

    with patch('medical_notes_processor.agents.extraction_agent.extract_structured_data') as mock_extract:
        mock_extract.return_value = {
            "patient": {"name": "Emma Smith", "date_of_birth": "2019-01-15", "age": "5 years"},
            "vital_signs": {"weight": "18 kg", "height": "110 cm"}
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

    with patch('medical_notes_processor.agents.extraction_agent.extract_structured_data') as mock_extract:
        mock_extract.return_value = {
            "lab_results": [
                {"test": "Hemoglobin A1c", "value": "8.2%", "status": "elevated"},
                {"test": "Creatinine", "value": "1.3 mg/dL"},
                {"test": "eGFR", "value": "55 mL/min/1.73m²"}
            ]
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

    with patch('medical_notes_processor.agents.extraction_agent.extract_structured_data') as mock_extract:
        mock_extract.return_value = {
            "patient": {"name": "María González"},
            "conditions": [{"name": "Diabetes tipo 2"}],
            "medications": [{"name": "Metformina", "dosage": "500mg"}]
        }

        response = await client.post("/extract_structured", json=note_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_extremely_long_note(client: AsyncClient):
    """Test extraction with very long medical note."""
    long_history = "Patient has extensive medical history. " * 2000
    note_data = {"text": long_history}

    with patch('medical_notes_processor.agents.extraction_agent.extract_structured_data') as mock_extract:
        mock_extract.return_value = {
            "patient": None,
            "conditions": [],
            "medications": []
        }

        response = await client.post("/extract_structured", json=note_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_special_medical_symbols(client: AsyncClient):
    """Test extraction with special medical symbols."""
    note_data = {
        "text": "Patient c/o ↑ BP & ♂ pattern baldness. Rx: ↓ Na+ intake, ↑ exercise"
    }

    with patch('medical_notes_processor.agents.extraction_agent.extract_structured_data') as mock_extract:
        mock_extract.return_value = {
            "conditions": [{"name": "Hypertension"}, {"name": "Male pattern baldness"}],
            "plan_actions": [
                {"action_type": "lifestyle", "description": "Decrease sodium intake"},
                {"action_type": "lifestyle", "description": "Increase exercise"}
            ]
        }

        response = await client.post("/extract_structured", json=note_data)
        assert response.status_code == 200
