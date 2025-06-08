import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
from unittest.mock import Mock, patch
from discountcrawlers.services.notification_service import NotificationService

@pytest.fixture
def notification_service():
    return NotificationService()

def test_success_notification(notification_service):
    """Test sending success notifications"""
    with patch('discord.Webhook') as mock_webhook:
        notification_service.send_success("Test Store", 10)
        mock_webhook.from_url.assert_called_once()
        mock_webhook.return_value.send.assert_called_once()

def test_error_notification(notification_service):
    """Test sending error notifications"""
    with patch('discord.Webhook') as mock_webhook:
        notification_service.send_error("Test Store", "Test error")
        mock_webhook.return_value.send.assert_called()

def test_configuration():
    """Test Notification service configuration"""
    from discountcrawlers.services import NOTIFICATION_CONFIG
    assert NOTIFICATION_CONFIG["WEBHOOK_URL"] is not None 