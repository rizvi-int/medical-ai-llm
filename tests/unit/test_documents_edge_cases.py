import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_document_with_very_long_title(client: AsyncClient):
    """Test document creation with extremely long title."""
    long_title = "A" * 10000
    document_data = {
        "title": long_title,
        "content": "Test content"
    }

    response = await client.post("/documents", json=document_data)
    # Should either succeed or return validation error
    assert response.status_code in [201, 422]


@pytest.mark.asyncio
async def test_create_document_with_very_long_content(client: AsyncClient):
    """Test document creation with very large content."""
    large_content = "Medical note content. " * 50000
    document_data = {
        "title": "Large Medical Record",
        "content": large_content
    }

    response = await client.post("/documents", json=document_data)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_document_with_special_characters(client: AsyncClient):
    """Test document creation with special medical characters."""
    document_data = {
        "title": "SOAP Note - Patient w/ BP & O2",
        "content": "S: Patient c/o BP\nO: T 98.6F, HR ~72 bpm\nA: HTN"
    }

    response = await client.post("/documents", json=document_data)
    assert response.status_code == 201

    data = response.json()
    assert data["title"] == document_data["title"]


@pytest.mark.asyncio
async def test_create_document_with_unicode(client: AsyncClient):
    """Test document creation with international characters."""
    document_data = {
        "title": "Nota Medica - Jose Garcia-Muller",
        "content": "Paciente: Jose Garcia\nDiagnostico: Hipertension arterial"
    }

    response = await client.post("/documents", json=document_data)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_document_with_newlines(client: AsyncClient):
    """Test document creation with various newline formats."""
    document_data = {
        "title": "Multi-line SOAP Note",
        "content": "S:\nPatient reports headache\n\nO:\nBP 120/80\r\n\r\nA:\nTension headache"
    }

    response = await client.post("/documents", json=document_data)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_document_null_values(client: AsyncClient):
    """Test document creation with null values."""
    invalid_data = {"title": None, "content": None}
    response = await client.post("/documents", json=invalid_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_document_numeric_fields(client: AsyncClient):
    """Test document creation with numeric values instead of strings."""
    invalid_data = {"title": 12345, "content": 67890}
    response = await client.post("/documents", json=invalid_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_document_with_invalid_id_type(client: AsyncClient):
    """Test getting document with non-numeric ID."""
    response = await client.get("/documents/not-a-number")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_document_with_negative_id(client: AsyncClient):
    """Test getting document with negative ID."""
    response = await client.get("/documents/-1")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_document_with_zero_id(client: AsyncClient):
    """Test getting document with ID zero."""
    response = await client.get("/documents/0")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_document(client: AsyncClient):
    """Test deleting a document that doesn't exist."""
    response = await client.delete("/documents/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_twice(client: AsyncClient):
    """Test deleting the same document twice."""
    # Create a document
    document_data = {"title": "Test", "content": "Test content"}
    create_response = await client.post("/documents", json=document_data)
    doc_id = create_response.json()["id"]

    # Delete it once
    response1 = await client.delete(f"/documents/{doc_id}")
    assert response1.status_code == 204

    # Try to delete again
    response2 = await client.delete(f"/documents/{doc_id}")
    assert response2.status_code == 404


@pytest.mark.asyncio
async def test_create_multiple_documents_same_title(client: AsyncClient):
    """Test creating multiple documents with identical titles."""
    document_data = {"title": "Duplicate Title", "content": "Content 1"}
    response1 = await client.post("/documents", json=document_data)
    assert response1.status_code == 201

    document_data = {"title": "Duplicate Title", "content": "Content 2"}
    response2 = await client.post("/documents", json=document_data)
    assert response2.status_code == 201

    # Both should have different IDs
    assert response1.json()["id"] != response2.json()["id"]


@pytest.mark.asyncio
async def test_get_all_documents_many_records(client: AsyncClient):
    """Test getting all documents when many exist."""
    # Create 20 documents
    for i in range(20):
        document_data = {"title": f"Document {i}", "content": f"Content {i}"}
        await client.post("/documents", json=document_data)

    response = await client.get("/documents/all")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 20


@pytest.mark.asyncio
async def test_create_document_with_html_content(client: AsyncClient):
    """Test document creation with HTML-like content."""
    document_data = {
        "title": "HTML Test",
        "content": "<b>Bold text</b> and <script>alert('xss')</script>"
    }

    response = await client.post("/documents", json=document_data)
    assert response.status_code == 201

    # Verify content is stored as-is (not executed)
    data = response.json()
    assert "<b>Bold text</b>" in data["content"]


@pytest.mark.asyncio
async def test_create_document_with_sql_injection_attempt(client: AsyncClient):
    """Test document creation with SQL injection patterns."""
    document_data = {
        "title": "'; DROP TABLE documents; --",
        "content": "1' OR '1'='1"
    }

    response = await client.post("/documents", json=document_data)
    assert response.status_code == 201

    # Verify the database wasn't affected
    all_docs = await client.get("/documents/all")
    assert all_docs.status_code == 200


@pytest.mark.asyncio
async def test_create_document_whitespace_only_title(client: AsyncClient):
    """Test document creation with whitespace-only title."""
    document_data = {"title": "   \t\n   ", "content": "Content"}
    response = await client.post("/documents", json=document_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_document_whitespace_only_content(client: AsyncClient):
    """Test document creation with whitespace-only content."""
    document_data = {"title": "Title", "content": "   \t\n   "}
    response = await client.post("/documents", json=document_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_document_with_very_large_id(client: AsyncClient):
    """Test getting document with extremely large ID."""
    response = await client.get("/documents/999999999999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_document_with_tabs_and_special_whitespace(client: AsyncClient):
    """Test document creation with tabs and special whitespace."""
    document_data = {
        "title": "Tab\tSeparated\tTitle",
        "content": "Line 1\t\tData\nLine 2\t\tMore Data"
    }

    response = await client.post("/documents", json=document_data)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_document_with_control_characters(client: AsyncClient):
    """Test document creation with control characters."""
    document_data = {
        "title": "Control Test",
        "content": "Text with\x00null\x01char\x02acters"
    }

    response = await client.post("/documents", json=document_data)
    # Should handle gracefully (either accept or reject)
    assert response.status_code in [201, 422]
