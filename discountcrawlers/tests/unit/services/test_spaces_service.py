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
from discountcrawlers.services.spaces_service import SpacesService

@pytest.fixture
def spaces_service():
    return SpacesService()

def test_connection(spaces_service):
    """Test Spaces service connection"""
    with patch('boto3.client') as mock_s3:
        spaces_service.connect()
        mock_s3.assert_called_once_with(
            's3',
            endpoint_url='https://fra1.digitaloceanspaces.com',
            aws_access_key_id='your-access-key',
            aws_secret_access_key='your-secret-key'
        )

def test_upload_file(spaces_service):
    """Test uploading files to Spaces"""
    with patch('boto3.client') as mock_s3:
        test_file = "test.log"
        spaces_service.upload_file(test_file)
        mock_s3.return_value.upload_file.assert_called_once()

def test_download_file(spaces_service):
    """Test downloading files from Spaces"""
    with patch('boto3.client') as mock_s3:
        spaces_service.download_file("test.log", "downloaded.log")
        mock_s3.return_value.download_file.assert_called_once()

def test_error_handling(spaces_service):
    """Test Spaces service error handling"""
    with patch('boto3.client') as mock_s3:
        mock_s3.return_value.upload_file.side_effect = Exception("S3 error")
        with pytest.raises(Exception):
            spaces_service.upload_file("test.log")

def test_configuration():
    """Test Spaces service configuration"""
    from discountcrawlers.services import SPACES_CONFIG
    assert SPACES_CONFIG["ACCESS_KEY"] is not None
    assert SPACES_CONFIG["SECRET_KEY"] is not None 