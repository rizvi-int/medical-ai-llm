import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_answer_question_success(client: AsyncClient):
    """Test successful RAG question answering."""
    question_data = {
        "question": "What medications were prescribed?"
    }

    with patch('medical_notes_processor.services.rag_service.get_rag_service') as mock_rag:
        mock_service = AsyncMock()
        mock_service.answer_question.return_value = {
            "answer": "Metformin 500mg twice daily and Lisinopril 10mg daily were prescribed.",
            "sources": [{"document_id": 1, "score": 0.95}]
        }
        mock_rag.return_value = mock_service

        response = await client.post("/answer_question", json=question_data)
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "sources" in data


@pytest.mark.asyncio
async def test_answer_empty_question(client: AsyncClient):
    """Test RAG with empty question."""
    question_data = {"question": ""}

    response = await client.post("/answer_question", json=question_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_answer_missing_question(client: AsyncClient):
    """Test RAG without question field."""
    question_data = {}

    response = await client.post("/answer_question", json=question_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_answer_whitespace_question(client: AsyncClient):
    """Test RAG with only whitespace question."""
    question_data = {"question": "   \n\t   "}

    response = await client.post("/answer_question", json=question_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_answer_very_long_question(client: AsyncClient):
    """Test RAG with very long question."""
    long_question = "What " + "medications " * 500 + "were prescribed?"
    question_data = {"question": long_question}

    with patch('medical_notes_processor.services.rag_service.get_rag_service') as mock_rag:
        mock_service = AsyncMock()
        mock_service.answer_question.return_value = {
            "answer": "The question was too long to process effectively.",
            "sources": []
        }
        mock_rag.return_value = mock_service

        response = await client.post("/answer_question", json=question_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_answer_medical_terminology_question(client: AsyncClient):
    """Test RAG with complex medical terminology."""
    question_data = {
        "question": "What was the patient's preoperative hemoglobin A1c and postprandial glucose levels?"
    }

    with patch('medical_notes_processor.services.rag_service.get_rag_service') as mock_rag:
        mock_service = AsyncMock()
        mock_service.answer_question.return_value = {
            "answer": "Hemoglobin A1c was 7.2%. Postprandial glucose levels ranged from 140-180 mg/dL.",
            "sources": [{"document_id": 2, "score": 0.88}]
        }
        mock_rag.return_value = mock_service

        response = await client.post("/answer_question", json=question_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_answer_question_no_context(client: AsyncClient):
    """Test RAG when no relevant documents found."""
    question_data = {
        "question": "What is the capital of France?"
    }

    with patch('medical_notes_processor.services.rag_service.get_rag_service') as mock_rag:
        mock_service = AsyncMock()
        mock_service.answer_question.return_value = {
            "answer": "I don't have information about that in the medical documents.",
            "sources": []
        }
        mock_rag.return_value = mock_service

        response = await client.post("/answer_question", json=question_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_answer_ambiguous_question(client: AsyncClient):
    """Test RAG with ambiguous question."""
    question_data = {
        "question": "What happened?"
    }

    with patch('medical_notes_processor.services.rag_service.get_rag_service') as mock_rag:
        mock_service = AsyncMock()
        mock_service.answer_question.return_value = {
            "answer": "The question is too vague. Please be more specific.",
            "sources": []
        }
        mock_rag.return_value = mock_service

        response = await client.post("/answer_question", json=question_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_answer_null_question(client: AsyncClient):
    """Test RAG with null question value."""
    question_data = {"question": None}

    response = await client.post("/answer_question", json=question_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_answer_numeric_question(client: AsyncClient):
    """Test RAG with numeric value instead of string."""
    question_data = {"question": 12345}

    response = await client.post("/answer_question", json=question_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_answer_special_characters_question(client: AsyncClient):
    """Test RAG with special characters in question."""
    question_data = {
        "question": "What was the pt's BP & HR? Was T° >100°F?"
    }

    with patch('medical_notes_processor.services.rag_service.get_rag_service') as mock_rag:
        mock_service = AsyncMock()
        mock_service.answer_question.return_value = {
            "answer": "Blood pressure was 130/80 mmHg, heart rate was 75 bpm. Temperature was 98.6°F.",
            "sources": [{"document_id": 1, "score": 0.92}]
        }
        mock_rag.return_value = mock_service

        response = await client.post("/answer_question", json=question_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_answer_multi_part_question(client: AsyncClient):
    """Test RAG with multiple questions in one."""
    question_data = {
        "question": "What medications was the patient on? What were their vital signs? Any allergies?"
    }

    with patch('medical_notes_processor.services.rag_service.get_rag_service') as mock_rag:
        mock_service = AsyncMock()
        mock_service.answer_question.return_value = {
            "answer": "Patient was on Metformin and Lisinopril. BP 130/80, HR 72. No known drug allergies.",
            "sources": [{"document_id": 1, "score": 0.90}]
        }
        mock_rag.return_value = mock_service

        response = await client.post("/answer_question", json=question_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_index_documents_success(client: AsyncClient):
    """Test successful document indexing."""
    with patch('medical_notes_processor.services.rag_service.get_rag_service') as mock_rag:
        mock_service = AsyncMock()
        mock_service.index_documents.return_value = {
            "indexed_count": 6,
            "status": "success"
        }
        mock_rag.return_value = mock_service

        response = await client.post("/index_documents")
        assert response.status_code == 200

        data = response.json()
        assert "indexed_count" in data


@pytest.mark.asyncio
async def test_answer_yes_no_question(client: AsyncClient):
    """Test RAG with yes/no question."""
    question_data = {
        "question": "Does the patient have diabetes?"
    }

    with patch('medical_notes_processor.services.rag_service.get_rag_service') as mock_rag:
        mock_service = AsyncMock()
        mock_service.answer_question.return_value = {
            "answer": "Yes, the patient has Type 2 Diabetes Mellitus.",
            "sources": [{"document_id": 1, "score": 0.95}]
        }
        mock_rag.return_value = mock_service

        response = await client.post("/answer_question", json=question_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_answer_date_specific_question(client: AsyncClient):
    """Test RAG with date-specific question."""
    question_data = {
        "question": "When was the patient's last visit?"
    }

    with patch('medical_notes_processor.services.rag_service.get_rag_service') as mock_rag:
        mock_service = AsyncMock()
        mock_service.answer_question.return_value = {
            "answer": "The patient's last visit was on 2024-03-15.",
            "sources": [{"document_id": 3, "score": 0.87}]
        }
        mock_rag.return_value = mock_service

        response = await client.post("/answer_question", json=question_data)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_answer_quantitative_question(client: AsyncClient):
    """Test RAG with quantitative question."""
    question_data = {
        "question": "How many medications is the patient taking?"
    }

    with patch('medical_notes_processor.services.rag_service.get_rag_service') as mock_rag:
        mock_service = AsyncMock()
        mock_service.answer_question.return_value = {
            "answer": "The patient is taking 5 medications.",
            "sources": [{"document_id": 1, "score": 0.93}]
        }
        mock_rag.return_value = mock_service

        response = await client.post("/answer_question", json=question_data)
        assert response.status_code == 200
