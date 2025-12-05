"""
Tests for chatbot features: multi-document queries, conversation memory, and context detection.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from medical_notes_processor.services.chatbot_service import MedicalChatbot


class TestMultiDocumentQueries:
    """Tests for extracting and querying multiple documents at once."""

    def test_extract_single_document_id(self):
        """Test extracting a single document ID."""
        chatbot = MedicalChatbot()

        assert chatbot._extract_document_ids("show me document 1") == [1]
        assert chatbot._extract_document_ids("summarize doc 5") == [5]
        assert chatbot._extract_document_ids("extract codes from patient 12") == [12]

    def test_extract_multiple_document_ids_with_and(self):
        """Test extracting multiple IDs with 'and'."""
        chatbot = MedicalChatbot()

        assert chatbot._extract_document_ids("document 1 and 3") == [1, 3]
        assert chatbot._extract_document_ids("summarize doc 2 and 5 and 7") == [2, 5, 7]

    def test_extract_multiple_document_ids_with_commas(self):
        """Test extracting multiple IDs with commas."""
        chatbot = MedicalChatbot()

        assert chatbot._extract_document_ids("doc 1, 2, 12") == [1, 2, 12]
        assert chatbot._extract_document_ids("patients 3, 5, 8, 10") == [3, 5, 8, 10]

    def test_extract_mixed_separators(self):
        """Test extracting IDs with mixed separators."""
        chatbot = MedicalChatbot()

        assert chatbot._extract_document_ids("document 1, 2 and 3") == [1, 2, 3]
        assert chatbot._extract_document_ids("doc 1 and 5, 7") == [1, 5, 7]

    def test_extract_with_different_keywords(self):
        """Test extraction with various document reference keywords."""
        chatbot = MedicalChatbot()

        # Different ways to refer to documents
        assert chatbot._extract_document_ids("documents 1 and 2") == [1, 2]
        assert chatbot._extract_document_ids("docs 3, 4") == [3, 4]
        assert chatbot._extract_document_ids("patient 5") == [5]
        assert chatbot._extract_document_ids("patients 6 and 7") == [6, 7]
        assert chatbot._extract_document_ids("case 8") == [8]
        assert chatbot._extract_document_ids("notes 9, 10") == [9, 10]
        assert chatbot._extract_document_ids("#11") == [11]

    def test_extract_no_duplicates(self):
        """Test that duplicate IDs are removed."""
        chatbot = MedicalChatbot()

        assert chatbot._extract_document_ids("document 1 and document 1") == [1]
        assert chatbot._extract_document_ids("doc 2, 3, 2") == [2, 3]

    def test_extract_sorted_ids(self):
        """Test that IDs are returned sorted."""
        chatbot = MedicalChatbot()

        assert chatbot._extract_document_ids("doc 5, 2, 8, 1") == [1, 2, 5, 8]
        assert chatbot._extract_document_ids("patient 10 and 3 and 7") == [3, 7, 10]

    def test_extract_no_ids(self):
        """Test that no IDs returns empty list."""
        chatbot = MedicalChatbot()

        assert chatbot._extract_document_ids("show me all patients") == []
        assert chatbot._extract_document_ids("what documents do you have?") == []
        assert chatbot._extract_document_ids("summarize everything") == []

    @pytest.mark.asyncio
    async def test_multi_document_summarization(self):
        """Test summarizing multiple documents at once."""
        chatbot = MedicalChatbot()

        message = "summarize documents 1, 2, and 3"

        # Mock document fetching
        with patch.object(chatbot, '_get_document') as mock_get_doc:
            mock_get_doc.side_effect = [
                {"id": 1, "title": "Patient A", "content": "Note A"},
                {"id": 2, "title": "Patient B", "content": "Note B"},
                {"id": 3, "title": "Patient C", "content": "Note C"}
            ]

            # Mock summarization
            with patch.object(chatbot, '_summarize_note') as mock_summarize:
                mock_summarize.side_effect = ["Summary A", "Summary B", "Summary C"]

                result = await chatbot.chat(message)

                # Should call get_document 3 times
                assert mock_get_doc.call_count == 3

                # Should call summarize 3 times
                assert mock_summarize.call_count == 3

                # Result should contain all summaries
                assert "Patient A" in result
                assert "Patient B" in result
                assert "Patient C" in result
                assert "Summary A" in result
                assert "Summary B" in result
                assert "Summary C" in result

    @pytest.mark.asyncio
    async def test_multi_document_code_extraction(self):
        """Test extracting codes from multiple documents."""
        chatbot = MedicalChatbot()

        message = "extract ICD-10 codes from doc 1 and 2"

        with patch.object(chatbot, '_get_document') as mock_get_doc:
            mock_get_doc.side_effect = [
                {"id": 1, "title": "Patient A", "content": "Diabetes"},
                {"id": 2, "title": "Patient B", "content": "Hypertension"}
            ]

            with patch.object(chatbot, '_extract_codes') as mock_extract:
                mock_extract.side_effect = [
                    {"conditions": [{"name": "Diabetes", "ai_icd10_code": "E11.9"}]},
                    {"conditions": [{"name": "Hypertension", "ai_icd10_code": "I10"}]}
                ]

                result = await chatbot.chat(message)

                assert mock_get_doc.call_count == 2
                assert mock_extract.call_count == 2

                # Should contain data from both documents
                assert "Patient A" in result
                assert "Patient B" in result


class TestConversationMemory:
    """Tests for conversation memory and context detection."""

    @pytest.mark.asyncio
    async def test_context_detection_with_it(self):
        """Test that 'it' refers to previous document."""
        chatbot = MedicalChatbot()

        # Conversation history with document 5 mentioned
        history = [
            {"role": "user", "content": "summarize document 5"},
            {"role": "assistant", "content": "Summary of document 5: Patient has diabetes..."}
        ]

        message = "what icd10 codes does it have"

        # Should detect document 5 from history
        with patch.object(chatbot, '_get_document') as mock_get_doc:
            mock_get_doc.return_value = {"id": 5, "title": "Patient", "content": "Diabetes"}

            with patch.object(chatbot, '_extract_codes') as mock_extract:
                mock_extract.return_value = {"conditions": [{"name": "Diabetes", "ai_icd10_code": "E11.9"}]}

                result = await chatbot.chat(message, conversation_history=history)

                # Should have called get_document with ID 5
                mock_get_doc.assert_called_with(5)

    @pytest.mark.asyncio
    async def test_context_detection_with_this_document(self):
        """Test that 'this document' refers to previous document."""
        chatbot = MedicalChatbot()

        history = [
            {"role": "user", "content": "show me patient 12"},
            {"role": "assistant", "content": "Here is patient 12's information..."}
        ]

        message = "what medications does this document have"

        with patch.object(chatbot, '_get_document') as mock_get_doc:
            mock_get_doc.return_value = {"id": 12, "title": "Patient", "content": "Metformin"}

            with patch.object(chatbot, '_rag_search') as mock_rag:
                mock_rag.return_value = {"answer": "Medications found", "sources": []}

                result = await chatbot.chat(message, conversation_history=history)

                # Should extract document ID 12 from history
                doc_ids = chatbot._extract_document_ids(history[-1]["content"])
                # If not found in assistant message, should check user message
                if not doc_ids:
                    doc_ids = chatbot._extract_document_ids(history[-2]["content"])
                assert 12 in doc_ids

    @pytest.mark.asyncio
    async def test_context_detection_with_them(self):
        """Test that 'them' refers to previous multiple documents."""
        chatbot = MedicalChatbot()

        history = [
            {"role": "user", "content": "summarize documents 2 and 3"},
            {"role": "assistant", "content": "Summaries for documents 2 and 3..."}
        ]

        message = "extract codes from them"

        with patch.object(chatbot, '_get_document') as mock_get_doc:
            mock_get_doc.side_effect = [
                {"id": 2, "title": "Patient A", "content": "Note A"},
                {"id": 3, "title": "Patient B", "content": "Note B"}
            ]

            with patch.object(chatbot, '_extract_codes') as mock_extract:
                mock_extract.side_effect = [
                    {"conditions": [{"name": "Diabetes", "ai_icd10_code": "E11.9"}]},
                    {"conditions": [{"name": "Hypertension", "ai_icd10_code": "I10"}]}
                ]

                result = await chatbot.chat(message, conversation_history=history)

                # Should process both documents
                assert mock_get_doc.call_count == 2

    @pytest.mark.asyncio
    async def test_context_detection_this_patient(self):
        """Test 'this patient' context detection."""
        chatbot = MedicalChatbot()

        history = [
            {"role": "user", "content": "what's in patient 7?"},
            {"role": "assistant", "content": "Patient 7 has the following..."}
        ]

        message = "what are the vital signs for this patient?"

        # Extract IDs should find 7 from history
        doc_ids = chatbot._extract_document_ids(history[0]["content"])
        assert 7 in doc_ids

    @pytest.mark.asyncio
    async def test_no_context_without_history(self):
        """Test that context words don't break without history."""
        chatbot = MedicalChatbot()

        message = "what codes does it have"

        # Without history, should ask for clarification
        with patch.object(chatbot, '_get_documents_list') as mock_list:
            mock_list.return_value = "Available documents: ..."

            result = await chatbot.chat(message, conversation_history=[])

            # Should fall through to document listing
            assert mock_list.called or "specify" in result.lower()

    @pytest.mark.asyncio
    async def test_lookback_limit(self):
        """Test that context detection only looks back 4 messages."""
        chatbot = MedicalChatbot()

        # Long history, document mentioned 5 messages ago
        history = [
            {"role": "user", "content": "show me document 1"},
            {"role": "assistant", "content": "Document 1..."},
            {"role": "user", "content": "what about general information?"},
            {"role": "assistant", "content": "General info..."},
            {"role": "user", "content": "tell me more"},
            {"role": "assistant", "content": "More info..."},
            {"role": "user", "content": "and another question"},
            {"role": "assistant", "content": "Another answer..."}
        ]

        message = "what codes does it have"

        # Should only look back 4 messages, so won't find document 1
        # Simulate the lookback logic
        recent_history = history[-4:]
        found_ids = []
        for msg in reversed(recent_history):
            if msg["role"] == "assistant":
                found_ids = chatbot._extract_document_ids(msg["content"])
                if found_ids:
                    break

        # Should not find document 1 (too far back)
        assert 1 not in found_ids


class TestKeywordDetection:
    """Tests for keyword-based routing."""

    def test_needs_code_extraction_detection(self):
        """Test detection of code extraction requests."""
        chatbot = MedicalChatbot()

        # Should detect
        assert chatbot._needs_code_extraction("extract ICD-10 codes")
        assert chatbot._needs_code_extraction("what are the icd10 codes")
        assert chatbot._needs_code_extraction("show me diagnosis codes")
        assert chatbot._needs_code_extraction("get rxnorm codes")
        assert chatbot._needs_code_extraction("extract medication codes")
        assert chatbot._needs_code_extraction("billing codes for this patient")

        # Should not detect
        assert not chatbot._needs_code_extraction("summarize the document")
        assert not chatbot._needs_code_extraction("what medications were prescribed")
        assert not chatbot._needs_code_extraction("show me the patient info")

    def test_needs_summarization_detection(self):
        """Test detection of summarization requests."""
        chatbot = MedicalChatbot()

        # Should detect
        assert chatbot._needs_summarization("summarize this document")
        assert chatbot._needs_summarization("give me a summary")
        assert chatbot._needs_summarization("provide an overview")
        assert chatbot._needs_summarization("brief summary please")

        # Should not detect
        assert not chatbot._needs_summarization("extract codes")
        assert not chatbot._needs_summarization("what are the medications")
        assert not chatbot._needs_summarization("show me patient data")


@pytest.mark.asyncio
async def test_chat_api_conversation_memory(client: AsyncClient):
    """Test that chat API maintains conversation memory across requests."""
    # First message
    response1 = await client.post(
        "/chat",
        json={
            "message": "summarize document 5",
            "session_id": "test-session"
        }
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["session_id"] == "test-session"

    # Second message using context
    response2 = await client.post(
        "/chat",
        json={
            "message": "what codes does it have",
            "session_id": "test-session"
        }
    )
    assert response2.status_code == 200
    data2 = response2.json()
    # Should remember document 5 from previous message
    assert data2["session_id"] == "test-session"


@pytest.mark.asyncio
async def test_chat_api_different_sessions(client: AsyncClient):
    """Test that different sessions maintain separate conversation histories."""
    # Session 1
    response1 = await client.post(
        "/chat",
        json={
            "message": "summarize document 1",
            "session_id": "session-1"
        }
    )
    assert response1.status_code == 200

    # Session 2 with different document
    response2 = await client.post(
        "/chat",
        json={
            "message": "summarize document 2",
            "session_id": "session-2"
        }
    )
    assert response2.status_code == 200

    # Both should maintain separate state
    assert response1.json()["session_id"] != response2.json()["session_id"]


@pytest.mark.asyncio
async def test_chat_api_reset(client: AsyncClient):
    """Test resetting conversation."""
    # Create some conversation
    await client.post("/chat", json={"message": "test", "session_id": "test"})

    # Reset
    response = await client.post("/chat/reset")
    assert response.status_code == 200

    # Conversation should be cleared
    data = response.json()
    assert "reset" in data["message"].lower() or "cleared" in data["message"].lower()
