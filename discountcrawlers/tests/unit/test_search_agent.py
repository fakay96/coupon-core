"""Unit tests for the SearchAgent class."""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from datetime import datetime
from django.utils import timezone

from discountcrawlers.agents.search_agent import SearchAgent
from discountcrawlers.models import Discount

@pytest.fixture
def search_agent():
    """Create a SearchAgent instance for testing."""
    return SearchAgent()

@pytest.fixture
def mock_discount():
    """Create a mock discount object."""
    discount = MagicMock(spec=Discount)
    discount.id = 1
    discount.retailer.name = "Test Retailer"
    discount.description = "Test discount"
    discount.discount_value = 10.0
    discount.category.name = "Test Category"
    discount.location = "Test Location"
    discount.embedding = np.random.rand(1024).tolist()
    discount.active = True
    return discount

def test_search_agent_initialization(search_agent):
    """Test SearchAgent initialization."""
    assert search_agent.context == {}
    assert search_agent.search_history == []

@patch('discountcrawlers.utils.embedding.generate_embedding')
def test_search_with_context(mock_generate_embedding, search_agent, mock_discount):
    """Test search with context."""
    # Setup
    mock_generate_embedding.return_value = np.random.rand(1024)
    Discount.objects.filter.return_value = [mock_discount]
    
    # Test
    context = {
        'location': 'Test Location',
        'categories': ['Test Category'],
        'preferences': {
            'retailers': ['Test Retailer'],
            'categories': ['Test Category']
        }
    }
    
    result = search_agent.search("test query", context)
    
    # Assertions
    assert 'query' in result
    assert 'results' in result
    assert 'metadata' in result
    assert result['context'] == context
    assert len(result['results']) > 0

@patch('discountcrawlers.utils.embedding.generate_embedding')
def test_search_with_filters(mock_generate_embedding, search_agent, mock_discount):
    """Test search with filters."""
    # Setup
    mock_generate_embedding.return_value = np.random.rand(1024)
    Discount.objects.filter.return_value = [mock_discount]
    
    # Test
    result = search_agent.search(
        "test query",
        location="Test Location",
        radius_km=5.0,
        categories=["Test Category"],
        min_discount=5.0,
        max_discount=15.0
    )
    
    # Assertions
    assert 'query' in result
    assert 'results' in result
    assert len(result['results']) > 0

def test_enhance_query_with_context(search_agent):
    """Test query enhancement with context."""
    # Setup
    search_agent.context = {
        'location': 'Test Location',
        'categories': ['Category1', 'Category2']
    }
    
    # Test
    enhanced_query = search_agent._enhance_query_with_context("test query")
    
    # Assertions
    assert "near Test Location" in enhanced_query
    assert "in categories: Category1, Category2" in enhanced_query

def test_calculate_similarity(search_agent):
    """Test similarity calculation."""
    # Setup
    vec1 = np.array([1, 0, 0])
    vec2 = np.array([0, 1, 0])
    
    # Test
    similarity = search_agent._calculate_similarity(vec1, vec2)
    
    # Assertions
    assert similarity == 0.0  # Orthogonal vectors
    
    # Test with identical vectors
    similarity = search_agent._calculate_similarity(vec1, vec1)
    assert similarity == 1.0  # Same vectors

def test_update_search_history(search_agent):
    """Test search history update."""
    # Setup
    query = "test query"
    response = {
        'results': [{'id': 1}, {'id': 2}],
        'metadata': {'total_results': 2}
    }
    
    # Test
    search_agent._update_search_history(query, response)
    
    # Assertions
    assert len(search_agent.search_history) == 1
    assert search_agent.search_history[0]['query'] == query
    assert search_agent.search_history[0]['results_count'] == 2

def test_create_error_response(search_agent):
    """Test error response creation."""
    # Test
    error_message = "Test error"
    response = search_agent._create_error_response(error_message)
    
    # Assertions
    assert response['error'] is True
    assert response['message'] == error_message
    assert 'timestamp' in response 