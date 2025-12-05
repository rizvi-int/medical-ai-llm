import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import os

# Skip tests requiring OpenAI API
pytestmark = pytest.mark.skipif(
    os.getenv("OPENAI_API_KEY", "").startswith("your-") or not os.getenv("OPENAI_API_KEY"),
    reason="OpenAI API key not configured"
)


@pytest.mark.asyncio
async def test_summarize_note_success(client: AsyncClient):
    """Test successful medical note summarization."""
    note_data = {
        "text": "S: Patient reports headache.\nO: BP 120/80\nA: Tension headache\nP: Rest and hydration"
    }

    with patch('medical_notes_processor.services.llm_service.llm_service.summarize_medical_note') as mock_summarize:
        mock_summarize.return_value = {
            "summary": "Patient presents with tension headache. Vital signs stable. Plan: conservative management.",
            "model_used": "gpt-4-turbo-preview"
        }

        response = await client.post("/summarize_note", json=note_data)
        assert response.status_code == 200

        data = response.json()
        assert "summary" in data
        assert "model_used" in data
        assert "tension headache" in data["summary"].lower()


@pytest.mark.asyncio
async def test_summarize_empty_text(client: AsyncClient):
    """Test summarization with empty text."""
    note_data = {"text": ""}

    response = await client.post("/summarize_note", json=note_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_summarize_missing_text_field(client: AsyncClient):
    """Test summarization with missing text field."""
    note_data = {}

    response = await client.post("/summarize_note", json=note_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_summarize_whitespace_only(client: AsyncClient):
    """Test summarization with only whitespace."""
    note_data = {"text": "   \n\t   "}

    response = await client.post("/summarize_note", json=note_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_summarize_very_long_text(client: AsyncClient):
    """Test summarization with very long text (token limit edge case)."""
    # Create a very long note (simulating edge of token limits)
    long_text = "Patient history: " + "Very detailed medical history. " * 1000
    note_data = {"text": long_text}

    with patch('medical_notes_processor.services.llm_service.llm_service.summarize_medical_note') as mock_summarize:
        mock_summarize.return_value = {
            "summary": "Extensive patient history documented.",
            "model_used": "gpt-4-turbo-preview"
        }

        response = await client.post("/summarize_note", json=note_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_summarize_special_characters(client: AsyncClient):
    """Test summarization with special medical characters."""
    note_data = {
        "text": "S: Patient c/o ↑ BP & ♂ pattern baldness\nO: T° 98.6°F, HR ~72 bpm\nA: HTN ± genetic component"
    }

    with patch('medical_notes_processor.services.llm_service.llm_service.summarize_medical_note') as mock_summarize:
        mock_summarize.return_value = {
            "summary": "Patient with elevated blood pressure.",
            "model_used": "gpt-4-turbo-preview"
        }

        response = await client.post("/summarize_note", json=note_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_summarize_unicode_characters(client: AsyncClient):
    """Test summarization with international characters."""
    note_data = {
        "text": "Paciente: José García-Müller\nDiagnóstico: Hipertensión"
    }

    with patch('medical_notes_processor.services.llm_service.llm_service.summarize_medical_note') as mock_summarize:
        mock_summarize.return_value = {
            "summary": "Patient José García-Müller with hypertension.",
            "model_used": "gpt-4-turbo-preview"
        }

        response = await client.post("/summarize_note", json=note_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_summarize_malformed_json(client: AsyncClient):
    """Test summarization with malformed JSON."""
    response = await client.post(
        "/summarize_note",
        content=b'{text: "missing quotes"}',
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_summarize_wrong_content_type(client: AsyncClient):
    """Test summarization with wrong content type."""
    response = await client.post(
        "/summarize_note",
        content="text=some medical note",
        headers={"Content-Type": "text/plain"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_summarize_null_text(client: AsyncClient):
    """Test summarization with null text value."""
    note_data = {"text": None}

    response = await client.post("/summarize_note", json=note_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_summarize_numeric_text(client: AsyncClient):
    """Test summarization with numeric value instead of string."""
    note_data = {"text": 12345}

    response = await client.post("/summarize_note", json=note_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_summarize_array_text(client: AsyncClient):
    """Test summarization with array instead of string."""
    note_data = {"text": ["line1", "line2"]}

    response = await client.post("/summarize_note", json=note_data)
    assert response.status_code == 422
