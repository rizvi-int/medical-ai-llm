"""
Tests for dual ICD-10 code extraction feature.

Tests both AI-inferred codes (from LLM) and API-validated codes (from Clinical Tables API).
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_dual_code_extraction_routine_exam(client: AsyncClient):
    """Test that AI assigns codes for routine exam but API may not find them."""
    note_data = {
        "text": """
        Patient: John Doe, DOB 1980-05-15
        Chief Complaint: Annual health examination

        Assessment: Adult annual health exam, all findings within normal limits.
        Patient appears healthy. Continue routine screening.
        """
    }

    with patch('medical_notes_processor.agents.extraction_agent.extraction_agent.llm') as mock_llm:
        # Mock LLM to return AI-suggested codes
        mock_response = AsyncMock()
        mock_response.content = """
        {
            "patient": {"name": "John Doe", "date_of_birth": "1980-05-15"},
            "encounter_date": "2024-01-15",
            "chief_complaint": "Annual health examination",
            "assessment": "Adult annual health exam, all findings within normal limits",
            "conditions": [
                {"name": "Adult annual health exam", "status": "active", "suggested_icd10_code": "Z00.00"}
            ]
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        # Mock API validation - may or may not find code
        with patch('medical_notes_processor.utils.external_apis.external_api_client.get_icd10_code') as mock_api:
            mock_api.return_value = None  # API doesn't find it

            response = await client.post("/extract_structured", json=note_data)
            assert response.status_code == 200

            data = response.json()
            conditions = data.get("structured_data", {}).get("conditions", [])

            # Should have AI-inferred code
            assert len(conditions) > 0
            assert conditions[0].get("ai_icd10_code") == "Z00.00"
            # But no validated code since API didn't find it
            assert "validated_icd10_code" not in conditions[0] or conditions[0].get("validated_icd10_code") is None


@pytest.mark.asyncio
async def test_dual_code_extraction_family_history(client: AsyncClient):
    """Test AI assigns family history codes that API may not recognize."""
    note_data = {
        "text": """
        Social History:
        - Family history of hyperlipidemia (father and brother)
        - Family history of hypertension (mother)

        Assessment: Patient at increased risk due to family history.
        Recommend regular lipid screening.
        """
    }

    with patch('medical_notes_processor.agents.extraction_agent.extraction_agent.llm') as mock_llm:
        mock_response = AsyncMock()
        mock_response.content = """
        {
            "assessment": "Patient at increased risk due to family history",
            "conditions": [
                {"name": "Family history of hyperlipidemia", "status": "documented", "suggested_icd10_code": "Z83.42"},
                {"name": "Family history of hypertension", "status": "documented", "suggested_icd10_code": "Z82.49"}
            ]
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch('medical_notes_processor.utils.external_apis.external_api_client.get_icd10_code') as mock_api:
            # API might find one but not the other
            mock_api.side_effect = ["Z83.42", None]

            response = await client.post("/extract_structured", json=note_data)
            assert response.status_code == 200

            data = response.json()
            conditions = data.get("structured_data", {}).get("conditions", [])

            assert len(conditions) == 2
            # First condition has both codes
            assert conditions[0].get("ai_icd10_code") == "Z83.42"
            assert conditions[0].get("validated_icd10_code") == "Z83.42"

            # Second condition only has AI code
            assert conditions[1].get("ai_icd10_code") == "Z82.49"
            assert "validated_icd10_code" not in conditions[1] or conditions[1].get("validated_icd10_code") is None


@pytest.mark.asyncio
async def test_dual_code_extraction_screening_codes(client: AsyncClient):
    """Test AI assigns screening codes for observations."""
    note_data = {
        "text": """
        Vital Signs:
        - Height: 175cm
        - Weight: 85kg
        - BMI: 27.8 (Possible overweight)

        Assessment: Patient appears slightly overweight. Recommend dietary counseling.
        """
    }

    with patch('medical_notes_processor.agents.extraction_agent.extraction_agent.llm') as mock_llm:
        mock_response = AsyncMock()
        mock_response.content = """
        {
            "vital_signs": {"height": "175cm", "weight": "85kg"},
            "assessment": "Patient appears slightly overweight",
            "conditions": [
                {"name": "Overweight", "status": "observation", "suggested_icd10_code": "E66.3"}
            ]
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch('medical_notes_processor.utils.external_apis.external_api_client.get_icd10_code') as mock_api:
            mock_api.return_value = "E66.3"  # API finds it

            response = await client.post("/extract_structured", json=note_data)
            assert response.status_code == 200

            data = response.json()
            conditions = data.get("structured_data", {}).get("conditions", [])

            assert len(conditions) > 0
            # Both AI and validated codes should match
            assert conditions[0].get("ai_icd10_code") == "E66.3"
            assert conditions[0].get("validated_icd10_code") == "E66.3"


@pytest.mark.asyncio
async def test_dual_code_extraction_confirmed_diagnosis(client: AsyncClient):
    """Test that confirmed diagnoses get both AI and validated codes."""
    note_data = {
        "text": """
        Diagnosis: Type 2 Diabetes Mellitus, uncontrolled

        Labs: HbA1c 9.2%

        Assessment: Patient with poorly controlled Type 2 Diabetes.
        Plan: Adjust medication regimen.
        """
    }

    with patch('medical_notes_processor.agents.extraction_agent.extraction_agent.llm') as mock_llm:
        mock_response = AsyncMock()
        mock_response.content = """
        {
            "assessment": "Patient with poorly controlled Type 2 Diabetes",
            "conditions": [
                {"name": "Type 2 Diabetes Mellitus", "status": "active", "suggested_icd10_code": "E11.9"}
            ],
            "lab_results": [
                {"test_name": "HbA1c", "value": "9.2", "unit": "%"}
            ]
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch('medical_notes_processor.utils.external_apis.external_api_client.get_icd10_code') as mock_api:
            mock_api.return_value = "E11.9"

            response = await client.post("/extract_structured", json=note_data)
            assert response.status_code == 200

            data = response.json()
            conditions = data.get("structured_data", {}).get("conditions", [])

            assert len(conditions) > 0
            # Both codes present and matching
            assert conditions[0].get("ai_icd10_code") == "E11.9"
            assert conditions[0].get("validated_icd10_code") == "E11.9"


@pytest.mark.asyncio
async def test_dual_code_extraction_multiple_conditions(client: AsyncClient):
    """Test dual codes for multiple conditions with mixed validation results."""
    note_data = {
        "text": """
        Problem List:
        1. Type 2 Diabetes Mellitus
        2. Essential Hypertension
        3. Screening for obesity (BMI 31)
        4. Annual wellness visit

        Plan: Continue current medications, repeat labs in 3 months.
        """
    }

    with patch('medical_notes_processor.agents.extraction_agent.extraction_agent.llm') as mock_llm:
        mock_response = AsyncMock()
        mock_response.content = """
        {
            "conditions": [
                {"name": "Type 2 Diabetes Mellitus", "status": "active", "suggested_icd10_code": "E11.9"},
                {"name": "Essential Hypertension", "status": "active", "suggested_icd10_code": "I10"},
                {"name": "Obesity", "status": "screening", "suggested_icd10_code": "E66.9"},
                {"name": "Annual wellness visit", "status": "encounter", "suggested_icd10_code": "Z00.00"}
            ]
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch('medical_notes_processor.utils.external_apis.external_api_client.get_icd10_code') as mock_api:
            # Simulate API finding some codes but not others
            mock_api.side_effect = ["E11.9", "I10", "E66.9", None]

            response = await client.post("/extract_structured", json=note_data)
            assert response.status_code == 200

            data = response.json()
            conditions = data.get("structured_data", {}).get("conditions", [])

            assert len(conditions) == 4

            # First three have validated codes
            for i in range(3):
                assert "ai_icd10_code" in conditions[i]
                assert "validated_icd10_code" in conditions[i]

            # Last one only has AI code
            assert conditions[3].get("ai_icd10_code") == "Z00.00"
            assert "validated_icd10_code" not in conditions[3] or conditions[3].get("validated_icd10_code") is None


@pytest.mark.asyncio
async def test_dual_code_chatbot_formatting(client: AsyncClient):
    """Test that chatbot formats dual codes correctly."""
    # This tests the _format_structured_data method in chatbot_service
    from medical_notes_processor.services.chatbot_service import MedicalChatbot

    chatbot = MedicalChatbot()

    # Structured data with dual codes
    structured_data = {
        "conditions": [
            {
                "name": "Adult annual health exam",
                "status": "active",
                "ai_icd10_code": "Z00.00",
                # No validated code - API didn't find it
            },
            {
                "name": "Type 2 Diabetes Mellitus",
                "status": "active",
                "ai_icd10_code": "E11.9",
                "validated_icd10_code": "E11.9"
            }
        ]
    }

    formatted = chatbot._format_structured_data(structured_data, "Test Document")

    # Should contain both sections
    assert "Diagnoses (AI-Inferred Codes):" in formatted
    assert "Diagnoses (API-Validated Codes):" in formatted

    # Should show both conditions in AI section
    assert "Adult annual health exam (ICD-10: Z00.00)" in formatted
    assert "Type 2 Diabetes Mellitus (ICD-10: E11.9)" in formatted

    # Should show validated codes section
    assert "Not found in database" in formatted  # For first condition


@pytest.mark.asyncio
async def test_backward_compatibility_old_format(client: AsyncClient):
    """Test that old format (single icd10_code field) still works."""
    from medical_notes_processor.services.chatbot_service import MedicalChatbot

    chatbot = MedicalChatbot()

    # Old format structured data
    structured_data = {
        "conditions": [
            {
                "name": "Type 2 Diabetes",
                "status": "active",
                "icd10_code": "E11.9"  # Old field name
            }
        ]
    }

    formatted = chatbot._format_structured_data(structured_data)

    # Should fall back to old format
    assert "Diagnoses:" in formatted
    assert "Type 2 Diabetes (ICD-10: E11.9)" in formatted
    # Should NOT have new format sections
    assert "AI-Inferred" not in formatted
    assert "API-Validated" not in formatted
