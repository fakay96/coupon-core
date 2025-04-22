"""Unit tests for the MetadataAgent class."""

import pytest
from unittest.mock import MagicMock, patch
import json
import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache

from discountcrawlers.agents.metadata_agent import MetadataAgent
from discountcrawlers.models import Discount

@pytest.fixture
def metadata_agent():
    """Create a MetadataAgent instance for testing."""
    return MetadataAgent()

@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    return {
        'id': 1,
        'description': 'Test discount description',
        'retailer': 'Test Retailer',
        'category': 'Test Category',
        'discount_value': 10.0
    }

@patch('discountcrawlers.utils.embedding.generate_embedding')
def test_process_metadata(mock_generate_embedding, metadata_agent, sample_metadata):
    """Test metadata processing."""
    # Setup
    mock_generate_embedding.return_value = np.random.rand(1024)
    
    # Test
    metadata_agent._process_metadata(sample_metadata)
    
    # Assertions
    assert len(metadata_agent.batch) == 1
    assert metadata_agent.batch[0] == sample_metadata

@patch('discountcrawlers.utils.embedding.generate_embedding')
def test_process_batch(mock_generate_embedding, metadata_agent, sample_metadata):
    """Test batch processing."""
    # Setup
    mock_generate_embedding.return_value = np.random.rand(1024)
    metadata_agent.batch = [sample_metadata]
    
    # Test
    metadata_agent._process_batch()
    
    # Assertions
    assert len(metadata_agent.batch) == 0
    assert metadata_agent.processing_stats['successful'] == 1
    assert metadata_agent.processing_stats['total_processed'] == 1

def test_store_metadata_with_cache(metadata_agent, sample_metadata):
    """Test metadata storage with cache hit."""
    # Setup
    cache_key = f"discount_embedding:{sample_metadata['id']}"
    cache.set(cache_key, np.random.rand(1024).tolist())
    
    # Test
    metadata_agent._store_metadata(sample_metadata)
    
    # Assertions
    assert metadata_agent.processing_stats['successful'] == 1

@patch('discountcrawlers.utils.embedding.generate_embedding')
def test_store_metadata_without_cache(mock_generate_embedding, metadata_agent, sample_metadata):
    """Test metadata storage without cache."""
    # Setup
    mock_generate_embedding.return_value = np.random.rand(1024)
    
    # Test
    metadata_agent._store_metadata(sample_metadata)
    
    # Assertions
    assert metadata_agent.processing_stats['successful'] == 1
    assert cache.get(f"discount_embedding:{sample_metadata['id']}") is not None

def test_retry_failed_items(metadata_agent, sample_metadata):
    """Test retry mechanism for failed items."""
    # Setup
    metadata_agent.batch = [sample_metadata]
    
    # Test
    metadata_agent._retry_failed_items()
    
    # Assertions
    assert len(metadata_agent.batch) == 0

def test_get_stats(metadata_agent):
    """Test statistics retrieval."""
    # Setup
    metadata_agent.processing_stats['total_processed'] = 10
    metadata_agent.processing_stats['successful'] = 8
    metadata_agent.processing_stats['failed'] = 2
    
    # Test
    stats = metadata_agent.get_stats()
    
    # Assertions
    assert stats['total_processed'] == 10
    assert stats['successful'] == 8
    assert stats['failed'] == 2
    assert 'batch_size' in stats
    assert 'time_since_last_process' in stats
    assert 'uptime' in stats

@patch('redis.Redis.pubsub')
def test_start_metadata_agent(mock_pubsub, metadata_agent):
    """Test metadata agent startup."""
    # Setup
    mock_pubsub.return_value.listen.return_value = [
        {'type': 'message', 'data': json.dumps({'id': 1, 'description': 'test'})}
    ]
    
    # Test
    metadata_agent.start()
    
    # Assertions
    mock_pubsub.return_value.subscribe.assert_called_once()

def test_handle_message_invalid_json(metadata_agent):
    """Test handling of invalid JSON messages."""
    # Test
    metadata_agent._handle_message(b'invalid json')
    
    # Assertions
    assert metadata_agent.processing_stats['failed'] == 1

@patch('discountcrawlers.utils.embedding.generate_embedding')
def test_handle_message_valid_json(mock_generate_embedding, metadata_agent, sample_metadata):
    """Test handling of valid JSON messages."""
    # Setup
    mock_generate_embedding.return_value = np.random.rand(1024)
    
    # Test
    metadata_agent._handle_message(json.dumps(sample_metadata).encode())
    
    # Assertions
    assert len(metadata_agent.batch) == 1
    assert metadata_agent.batch[0] == sample_metadata 