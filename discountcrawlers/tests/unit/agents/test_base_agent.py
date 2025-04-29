import pytest
from unittest.mock import Mock, patch, AsyncMock
from discountcrawlers.agents.base import BaseAgent
from discountcrawlers.items import DiscountItem

@pytest.fixture
def base_agent():
    return BaseAgent()

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
async def test_agent_initialization(base_agent):
    """Test base agent initialization"""
    assert base_agent.logger is not None
    assert base_agent.config is not None
    assert base_agent.state is not None

@pytest.mark.asyncio
async def test_agent_lifecycle(base_agent):
    """Test agent lifecycle methods"""
    # Test start
    await base_agent.start()
    assert base_agent.state == "running"
    
    # Test stop
    await base_agent.stop()
    assert base_agent.state == "stopped"

@pytest.mark.asyncio
async def test_error_handling(base_agent):
    """Test error handling in base agent"""
    # Test start error
    with patch.object(base_agent, '_initialize', side_effect=Exception("Init error")):
        with pytest.raises(Exception):
            await base_agent.start()
    
    # Test stop error
    with patch.object(base_agent, '_cleanup', side_effect=Exception("Cleanup error")):
        with pytest.raises(Exception):
            await base_agent.stop()

@pytest.mark.asyncio
async def test_state_management(base_agent):
    """Test state management in base agent"""
    # Test state transitions
    assert base_agent.state == "initialized"
    await base_agent.start()
    assert base_agent.state == "running"
    await base_agent.stop()
    assert base_agent.state == "stopped"
    
    # Test invalid state transition
    with pytest.raises(ValueError):
        await base_agent.start()  # Already stopped

@pytest.mark.asyncio
async def test_configuration_handling(base_agent):
    """Test configuration handling in base agent"""
    # Test config loading
    assert base_agent.config is not None
    assert isinstance(base_agent.config, dict)
    
    # Test config validation
    required_keys = ['log_level', 'max_retries', 'timeout']
    for key in required_keys:
        assert key in base_agent.config

@pytest.mark.asyncio
async def test_logging(base_agent):
    """Test logging functionality in base agent"""
    with patch('logging.Logger') as mock_logger:
        # Test info logging
        base_agent.log_info("Test info")
        mock_logger.info.assert_called_once_with("Test info")
        
        # Test error logging
        base_agent.log_error("Test error")
        mock_logger.error.assert_called_once_with("Test error")
        
        # Test debug logging
        base_agent.log_debug("Test debug")
        mock_logger.debug.assert_called_once_with("Test debug")

@pytest.mark.asyncio
async def test_retry_mechanism(base_agent):
    """Test retry mechanism in base agent"""
    with patch('asyncio.sleep') as mock_sleep:
        # Test successful operation
        @base_agent.retry_on_failure
        async def successful_operation():
            return "success"
        
        result = await successful_operation()
        assert result == "success"
        assert not mock_sleep.called
        
        # Test failing operation
        @base_agent.retry_on_failure
        async def failing_operation():
            raise Exception("Test error")
        
        with pytest.raises(Exception):
            await failing_operation()
        assert mock_sleep.call_count == base_agent.config['max_retries']

@pytest.mark.asyncio
async def test_metrics_collection(base_agent):
    """Test metrics collection in base agent"""
    # Test operation timing
    with patch('time.time') as mock_time:
        mock_time.side_effect = [0, 1]  # 1 second operation
        await base_agent.start()
        assert base_agent.metrics['start_time'] == 0
        assert base_agent.metrics['operation_duration'] == 1.0
    
    # Test error counting
    base_agent.increment_error_count()
    assert base_agent.metrics['error_count'] == 1
    
    # Test operation counting
    base_agent.increment_operation_count()
    assert base_agent.metrics['operation_count'] == 1 