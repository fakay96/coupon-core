import pytest
from unittest.mock import Mock, patch, AsyncMock
from discountcrawlers.agents.coordinator_agent import CoordinatorAgent
from discountcrawlers.agents.metadata_agent import MetadataAgent
from discountcrawlers.agents.search_agent import SearchAgent

@pytest.fixture
def coordinator_agent():
    return CoordinatorAgent()

@pytest.fixture
def mock_agents():
    return {
        "metadata": Mock(spec=MetadataAgent),
        "search": Mock(spec=SearchAgent)
    }

@pytest.mark.asyncio
async def test_agent_initialization(coordinator_agent):
    """Test coordinator agent initialization"""
    assert coordinator_agent.logger is not None
    assert coordinator_agent.config is not None
    assert coordinator_agent.state == "initialized"
    assert coordinator_agent.agents is not None

@pytest.mark.asyncio
async def test_agent_registration(coordinator_agent, mock_agents):
    """Test agent registration"""
    for name, agent in mock_agents.items():
        coordinator_agent.register_agent(name, agent)
    
    assert len(coordinator_agent.agents) == len(mock_agents)
    for name in mock_agents:
        assert name in coordinator_agent.agents

@pytest.mark.asyncio
async def test_agent_coordination(coordinator_agent, mock_agents):
    """Test agent coordination"""
    # Register mock agents
    for name, agent in mock_agents.items():
        coordinator_agent.register_agent(name, agent)
    
    # Test starting all agents
    await coordinator_agent.start_all_agents()
    for agent in mock_agents.values():
        agent.start.assert_called_once()
    
    # Test stopping all agents
    await coordinator_agent.stop_all_agents()
    for agent in mock_agents.values():
        agent.stop.assert_called_once()

@pytest.mark.asyncio
async def test_task_distribution(coordinator_agent, mock_agents):
    """Test task distribution"""
    # Register mock agents
    for name, agent in mock_agents.items():
        coordinator_agent.register_agent(name, agent)
    
    # Test distributing tasks
    tasks = [
        {"type": "metadata", "data": {"test": "data1"}},
        {"type": "search", "data": {"test": "data2"}}
    ]
    
    await coordinator_agent.distribute_tasks(tasks)
    mock_agents["metadata"].process_task.assert_called_once()
    mock_agents["search"].process_task.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling(coordinator_agent, mock_agents):
    """Test error handling in coordinator agent"""
    # Register mock agents
    for name, agent in mock_agents.items():
        coordinator_agent.register_agent(name, agent)
    
    # Test agent start error
    mock_agents["metadata"].start.side_effect = Exception("Start error")
    with pytest.raises(Exception):
        await coordinator_agent.start_all_agents()
    
    # Test task distribution error
    mock_agents["search"].process_task.side_effect = Exception("Task error")
    with pytest.raises(Exception):
        await coordinator_agent.distribute_tasks([{"type": "search", "data": {}}])

@pytest.mark.asyncio
async def test_agent_health_check(coordinator_agent, mock_agents):
    """Test agent health checking"""
    # Register mock agents
    for name, agent in mock_agents.items():
        coordinator_agent.register_agent(name, agent)
    
    # Test health check
    health_status = await coordinator_agent.check_agent_health()
    assert isinstance(health_status, dict)
    for name in mock_agents:
        assert name in health_status
        assert "status" in health_status[name]
        assert "last_active" in health_status[name]

@pytest.mark.asyncio
async def test_agent_recovery(coordinator_agent, mock_agents):
    """Test agent recovery"""
    # Register mock agents
    for name, agent in mock_agents.items():
        coordinator_agent.register_agent(name, agent)
    
    # Test recovery after failure
    mock_agents["metadata"].state = "failed"
    await coordinator_agent.recover_failed_agents()
    mock_agents["metadata"].recover.assert_called_once()

@pytest.mark.asyncio
async def test_load_balancing(coordinator_agent, mock_agents):
    """Test load balancing"""
    # Register mock agents
    for name, agent in mock_agents.items():
        coordinator_agent.register_agent(name, agent)
    
    # Test load distribution
    tasks = [{"type": "metadata", "data": {}}] * 10
    await coordinator_agent.distribute_tasks(tasks)
    
    # Verify load is distributed evenly
    assert mock_agents["metadata"].process_task.call_count == 10

@pytest.mark.asyncio
async def test_agent_metrics(coordinator_agent, mock_agents):
    """Test agent metrics collection"""
    # Register mock agents
    for name, agent in mock_agents.items():
        coordinator_agent.register_agent(name, agent)
    
    # Test metrics collection
    metrics = await coordinator_agent.collect_metrics()
    assert isinstance(metrics, dict)
    assert "total_tasks" in metrics
    assert "success_rate" in metrics
    assert "average_processing_time" in metrics

@pytest.mark.asyncio
async def test_agent_configuration(coordinator_agent):
    """Test agent configuration management"""
    # Test configuration loading
    assert coordinator_agent.config is not None
    assert isinstance(coordinator_agent.config, dict)
    
    # Test configuration validation
    required_keys = ['max_agents', 'task_timeout', 'recovery_attempts']
    for key in required_keys:
        assert key in coordinator_agent.config 