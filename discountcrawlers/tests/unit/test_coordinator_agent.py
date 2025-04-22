"""Unit tests for the CoordinatorAgent class."""

import pytest
from unittest.mock import MagicMock, patch
import threading
from datetime import datetime
from django.utils import timezone
from django.core.cache import cache

from discountcrawlers.agents.coordinator_agent import CoordinatorAgent
from discountcrawlers.agents.search_agent import SearchAgent
from discountcrawlers.agents.metadata_agent import MetadataAgent

@pytest.fixture
def coordinator_agent():
    """Create a CoordinatorAgent instance for testing."""
    return CoordinatorAgent()

def test_coordinator_initialization(coordinator_agent):
    """Test CoordinatorAgent initialization."""
    assert isinstance(coordinator_agent.search_agent, SearchAgent)
    assert isinstance(coordinator_agent.metadata_agent, MetadataAgent)
    assert coordinator_agent.system_state['start_time'] is not None
    assert coordinator_agent.system_state['agents']['search']['status'] == 'initialized'
    assert coordinator_agent.system_state['agents']['metadata']['status'] == 'initialized'

@patch('threading.Thread')
def test_start_metadata_agent(mock_thread, coordinator_agent):
    """Test starting the metadata agent."""
    # Setup
    mock_thread_instance = MagicMock()
    mock_thread.return_value = mock_thread_instance
    
    # Test
    coordinator_agent._start_metadata_agent()
    
    # Assertions
    mock_thread.assert_called_once()
    mock_thread_instance.start.assert_called_once()

def test_process_search_request_success(coordinator_agent):
    """Test successful search request processing."""
    # Setup
    mock_response = {
        'query': 'test query',
        'results': [{'id': 1}],
        'metadata': {'total_results': 1}
    }
    coordinator_agent.search_agent.search = MagicMock(return_value=mock_response)
    
    # Test
    result = coordinator_agent.process_search_request('test query')
    
    # Assertions
    assert result == mock_response
    assert coordinator_agent.system_state['metrics']['successful_requests'] == 1
    assert coordinator_agent.system_state['metrics']['total_requests'] == 1

def test_process_search_request_failure(coordinator_agent):
    """Test failed search request processing."""
    # Setup
    coordinator_agent.search_agent.search = MagicMock(side_effect=Exception('Test error'))
    
    # Test
    result = coordinator_agent.process_search_request('test query')
    
    # Assertions
    assert result['error'] is True
    assert 'Test error' in result['message']
    assert coordinator_agent.system_state['metrics']['failed_requests'] == 1
    assert coordinator_agent.system_state['metrics']['total_requests'] == 1

def test_get_system_status(coordinator_agent):
    """Test system status retrieval."""
    # Setup
    coordinator_agent.metadata_agent.get_stats = MagicMock(return_value={
        'total_processed': 10,
        'successful': 8,
        'failed': 2
    })
    
    # Test
    status = coordinator_agent.get_system_status()
    
    # Assertions
    assert 'start_time' in status
    assert 'agents' in status
    assert 'errors' in status
    assert 'metrics' in status
    assert 'metadata_agent_stats' in status
    assert 'cache_status' in status

def test_handle_error(coordinator_agent):
    """Test error handling."""
    # Test
    error = Exception('Test error')
    coordinator_agent._handle_error(error)
    
    # Assertions
    assert len(coordinator_agent.system_state['errors']) == 1
    error_info = coordinator_agent.system_state['errors'][0]
    assert error_info['type'] == 'Exception'
    assert error_info['message'] == 'Test error'
    assert 'timestamp' in error_info

def test_get_cache_memory_usage(coordinator_agent):
    """Test cache memory usage calculation."""
    # Setup
    cache._cache = {
        'key1': 'value1',
        'key2': 'value2'
    }
    
    # Test
    usage = coordinator_agent._get_cache_memory_usage()
    
    # Assertions
    assert usage == len('key1') + len('value1') + len('key2') + len('value2')

def test_get_cache_memory_usage_empty(coordinator_agent):
    """Test cache memory usage calculation with empty cache."""
    # Setup
    cache._cache = {}
    
    # Test
    usage = coordinator_agent._get_cache_memory_usage()
    
    # Assertions
    assert usage == 0

def test_get_cache_memory_usage_error(coordinator_agent):
    """Test cache memory usage calculation with error."""
    # Setup
    cache._cache = None  # This will cause an error
    
    # Test
    usage = coordinator_agent._get_cache_memory_usage()
    
    # Assertions
    assert usage == 0 