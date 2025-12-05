import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_document(client: AsyncClient):
    """Test creating a new document."""
    document_data = {
        "title": "Test Medical Note",
        "content": "This is a test medical note content."
    }

    response = await client.post("/documents", json=document_data)
    assert response.status_code == 201

    data = response.json()
    assert data["title"] == document_data["title"]
    assert data["content"] == document_data["content"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_all_document_ids(client: AsyncClient):
    """Test getting all document IDs."""
    # Create a document first
    document_data = {
        "title": "Test Note",
        "content": "Test content"
    }
    await client.post("/documents", json=document_data)

    # Get all IDs
    response = await client.get("/documents")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_get_all_documents(client: AsyncClient):
    """Test getting all documents with full details."""
    # Create a document first
    document_data = {
        "title": "Test Note",
        "content": "Test content"
    }
    await client.post("/documents", json=document_data)

    # Get all documents
    response = await client.get("/documents/all")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "title" in data[0]
    assert "content" in data[0]


@pytest.mark.asyncio
async def test_get_document_by_id(client: AsyncClient):
    """Test getting a specific document by ID."""
    # Create a document first
    document_data = {
        "title": "Test Note",
        "content": "Test content"
    }
    create_response = await client.post("/documents", json=document_data)
    created_doc = create_response.json()

    # Get the document by ID
    response = await client.get(f"/documents/{created_doc['id']}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == created_doc["id"]
    assert data["title"] == document_data["title"]


@pytest.mark.asyncio
async def test_get_nonexistent_document(client: AsyncClient):
    """Test getting a document that doesn't exist."""
    response = await client.get("/documents/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient):
    """Test deleting a document."""
    # Create a document first
    document_data = {
        "title": "Test Note",
        "content": "Test content"
    }
    create_response = await client.post("/documents", json=document_data)
    created_doc = create_response.json()

    # Delete the document
    response = await client.delete(f"/documents/{created_doc['id']}")
    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(f"/documents/{created_doc['id']}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_create_document_validation(client: AsyncClient):
    """Test document creation with invalid data."""
    # Missing content
    invalid_data = {"title": "Test"}
    response = await client.post("/documents", json=invalid_data)
    assert response.status_code == 422

    # Missing title
    invalid_data = {"content": "Test content"}
    response = await client.post("/documents", json=invalid_data)
    assert response.status_code == 422

    # Empty title
    invalid_data = {"title": "", "content": "Test content"}
    response = await client.post("/documents", json=invalid_data)
    assert response.status_code == 422
