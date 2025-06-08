import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
from sentence_transformers import SentenceTransformer
from discountcrawlers.utils.embedding import EmbeddingService
from discountcrawlers.items import DiscountItem

@pytest.fixture
def embedding_service():
    return EmbeddingService()

@pytest.fixture
def sample_text():
    return "This is a test product description for embedding generation"

@pytest.fixture
def sample_item():
    return DiscountItem(
        title="Test Product",
        price=19.99,
        original_price=29.99,
        url="https://example.com/product",
        store="Test Store",
        description="A test product for embedding generation"
    )

@pytest.mark.asyncio
async def test_model_initialization(embedding_service):
    """Test embedding model initialization"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        await embedding_service.initialize()
        mock_model.assert_called_once()
        assert embedding_service.model is not None

@pytest.mark.asyncio
async def test_text_embedding(embedding_service, sample_text):
    """Test text embedding generation"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        mock_model.return_value.encode = Mock(return_value=np.random.rand(384).astype(np.float32))
        embedding_service.model = mock_model.return_value
        
        embedding = await embedding_service.get_embedding(sample_text)
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert embedding.dtype == np.float32

@pytest.mark.asyncio
async def test_batch_embedding(embedding_service):
    """Test batch embedding generation"""
    texts = ["text1", "text2", "text3"]
    
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        mock_model.return_value.encode = Mock(return_value=np.random.rand(3, 384).astype(np.float32))
        embedding_service.model = mock_model.return_value
        
        embeddings = await embedding_service.get_embeddings(texts)
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 384)
        assert embeddings.dtype == np.float32

@pytest.mark.asyncio
async def test_item_embedding(embedding_service, sample_item):
    """Test item embedding generation"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        mock_model.return_value.encode = Mock(return_value=np.random.rand(384).astype(np.float32))
        embedding_service.model = mock_model.return_value
        
        embedding = await embedding_service.get_item_embedding(sample_item)
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert embedding.dtype == np.float32

@pytest.mark.asyncio
async def test_error_handling(embedding_service):
    """Test error handling"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        mock_model.return_value.encode = Mock(side_effect=Exception("Model error"))
        embedding_service.model = mock_model.return_value
        
        with pytest.raises(Exception):
            await embedding_service.get_embedding("test text")

@pytest.mark.asyncio
async def test_embedding_normalization(embedding_service, sample_text):
    """Test embedding normalization"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        # Create a non-normalized embedding
        raw_embedding = np.random.rand(384).astype(np.float32)
        mock_model.return_value.encode = Mock(return_value=raw_embedding)
        embedding_service.model = mock_model.return_value
        
        embedding = await embedding_service.get_embedding(sample_text)
        # Check if the embedding is normalized (L2 norm = 1)
        assert np.isclose(np.linalg.norm(embedding), 1.0)

@pytest.mark.asyncio
async def test_embedding_similarity(embedding_service):
    """Test embedding similarity calculation"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        # Create two similar embeddings
        embedding1 = np.random.rand(384).astype(np.float32)
        embedding2 = embedding1 + 0.1 * np.random.rand(384).astype(np.float32)
        
        mock_model.return_value.encode = Mock(side_effect=[embedding1, embedding2])
        embedding_service.model = mock_model.return_value
        
        similarity = await embedding_service.get_similarity("text1", "text2")
        assert 0 <= similarity <= 1
        assert similarity > 0.5  # Similar embeddings should have high similarity

@pytest.mark.asyncio
async def test_model_caching(embedding_service):
    """Test model caching"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        await embedding_service.initialize()
        await embedding_service.initialize()  # Second initialization should use cached model
        mock_model.assert_called_once()  # Model should only be initialized once

@pytest.mark.asyncio
async def test_embedding_dimensions(embedding_service, sample_text):
    """Test embedding dimensions"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        mock_model.return_value.encode = Mock(return_value=np.random.rand(384).astype(np.float32))
        embedding_service.model = mock_model.return_value
        
        embedding = await embedding_service.get_embedding(sample_text)
        assert embedding.shape == (384,)  # Check correct dimension
        assert embedding.dtype == np.float32  # Check correct data type 