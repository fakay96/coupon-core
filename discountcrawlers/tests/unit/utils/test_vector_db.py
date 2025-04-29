import pytest
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
from discountcrawlers.utils.vector_db import VectorDB
from discountcrawlers.items import DiscountItem

@pytest.fixture
def vector_db():
    return VectorDB()

@pytest.fixture
def sample_embedding():
    return np.random.rand(384).astype(np.float32)

@pytest.fixture
def sample_item():
    return DiscountItem(
        title="Test Product",
        price=19.99,
        original_price=29.99,
        url="https://example.com/product",
        store="Test Store"
    )

@pytest.mark.asyncio
async def test_db_initialization(vector_db):
    """Test vector database initialization"""
    with patch('chromadb.Client') as mock_client:
        await vector_db.initialize()
        mock_client.assert_called_once()
        assert vector_db.client is not None
        assert vector_db.collection is not None

@pytest.mark.asyncio
async def test_embedding_storage(vector_db, sample_item, sample_embedding):
    """Test storing embeddings"""
    with patch('chromadb.Collection') as mock_collection:
        mock_collection.add = AsyncMock()
        vector_db.collection = mock_collection
        
        await vector_db.store_embedding(sample_item.url, sample_embedding)
        mock_collection.add.assert_called_once()

@pytest.mark.asyncio
async def test_similarity_search(vector_db, sample_embedding):
    """Test similarity search"""
    with patch('chromadb.Collection') as mock_collection:
        mock_collection.query = AsyncMock(return_value={
            'ids': [['doc1', 'doc2']],
            'distances': [[0.1, 0.2]],
            'metadatas': [[{'url': 'url1'}, {'url': 'url2'}]]
        })
        vector_db.collection = mock_collection
        
        results = await vector_db.search_similar(sample_embedding, k=2)
        assert len(results) == 2
        assert 'url1' in results
        assert 'url2' in results

@pytest.mark.asyncio
async def test_batch_operations(vector_db, sample_embedding):
    """Test batch operations"""
    urls = ['url1', 'url2', 'url3']
    embeddings = [sample_embedding] * 3
    
    with patch('chromadb.Collection') as mock_collection:
        mock_collection.add = AsyncMock()
        vector_db.collection = mock_collection
        
        await vector_db.store_embeddings(urls, embeddings)
        mock_collection.add.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling(vector_db):
    """Test error handling"""
    with patch('chromadb.Collection') as mock_collection:
        mock_collection.query = AsyncMock(side_effect=Exception("DB error"))
        vector_db.collection = mock_collection
        
        with pytest.raises(Exception):
            await vector_db.search_similar(np.random.rand(384).astype(np.float32))

@pytest.mark.asyncio
async def test_embedding_validation(vector_db, sample_embedding):
    """Test embedding validation"""
    # Test valid embedding
    assert vector_db._validate_embedding(sample_embedding) is True
    
    # Test invalid embedding (wrong shape)
    invalid_embedding = np.random.rand(100).astype(np.float32)
    with pytest.raises(ValueError):
        vector_db._validate_embedding(invalid_embedding)
    
    # Test invalid embedding (wrong type)
    invalid_embedding = np.random.rand(384).astype(np.float64)
    with pytest.raises(ValueError):
        vector_db._validate_embedding(invalid_embedding)

@pytest.mark.asyncio
async def test_collection_management(vector_db):
    """Test collection management"""
    with patch('chromadb.Client') as mock_client:
        mock_client.get_or_create_collection = AsyncMock()
        vector_db.client = mock_client
        
        await vector_db.ensure_collection()
        mock_client.get_or_create_collection.assert_called_once()

@pytest.mark.asyncio
async def test_cleanup(vector_db):
    """Test cleanup operations"""
    with patch('chromadb.Collection') as mock_collection:
        mock_collection.delete = AsyncMock()
        vector_db.collection = mock_collection
        
        await vector_db.cleanup()
        mock_collection.delete.assert_called_once()

@pytest.mark.asyncio
async def test_metrics_collection(vector_db):
    """Test metrics collection"""
    with patch('chromadb.Collection') as mock_collection:
        mock_collection.count = AsyncMock(return_value=100)
        vector_db.collection = mock_collection
        
        metrics = await vector_db.get_metrics()
        assert 'total_embeddings' in metrics
        assert metrics['total_embeddings'] == 100 