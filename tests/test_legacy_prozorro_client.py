from unittest.mock import patch, Mock
import pytest
import requests

from api.legacy_prozorro_client import LegacyProzorroClient

class TestLegacyProzorroClient:

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self):
        self.client = LegacyProzorroClient(retry_count=2, retry_delay=0)

    @patch('requests.get')
    def test_fetch_tender_details_success(self, mock_get):
        """Test the successful fetch of tender details using UUID."""
        # Arrange
        tender_uuid = "a1b2c3d4e5f67890a1b2c3d4e5f67890" # Example 32-char UUID
        mock_response = Mock()
        mock_response.status_code = 200
        # Mock response structure from the legacy API (with 'data' wrapper)
        mock_response.json.return_value = {
            "data": {
                "id": tender_uuid, # This is the UUID itself
                "tenderID": "UA-2024-01-01-000001-a", # This is the OCID
                "title": "Legacy Tender 1",
                "value": {"amount": 1000, "currency": "UAH"},
                "dateModified": "2024-01-01T12:00:00+02:00",
            }
        }
        mock_get.return_value = mock_response

        # Act
        result = self.client.fetch_tender_details(tender_uuid)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result["id"] == tender_uuid
        assert result["tenderID"] == "UA-2024-01-01-000001-a"
        assert result["title"] == "Legacy Tender 1"

        expected_url = f"{LegacyProzorroClient.BASE_URL}{tender_uuid}"
        mock_get.assert_called_once_with(
            expected_url,
            timeout=self.client.timeout
        )

    @patch('requests.get')
    def test_fetch_tender_details_http_error(self, mock_get):
        """Test handling of HTTP error response."""
        # Arrange
        tender_uuid = "a1b2c3d4e5f67890a1b2c3d4e5f67890"
        mock_response = Mock()
        mock_response.status_code = 404
        # Configure raise_for_status to raise an error
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
        mock_get.return_value = mock_response

        # Act
        result = self.client.fetch_tender_details(tender_uuid)

        # Assert
        assert result is None
        assert mock_get.call_count == self.client.retry_count

    @patch('requests.get')
    def test_fetch_tender_details_request_exception(self, mock_get):
        """Test handling of requests library exception."""
        # Arrange
        tender_uuid = "a1b2c3d4e5f67890a1b2c3d4e5f67890"
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        # Act
        result = self.client.fetch_tender_details(tender_uuid)

        # Assert
        assert result is None
        assert mock_get.call_count == self.client.retry_count

    @patch('requests.get')
    def test_fetch_tender_details_json_decode_error(self, mock_get):
        """Test handling of invalid JSON response."""
        # Arrange
        tender_uuid = "a1b2c3d4e5f67890a1b2c3d4e5f67890"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        # Simulate JSON decode error
        mock_response.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "", 0)
        mock_get.return_value = mock_response

        # Act
        result = self.client.fetch_tender_details(tender_uuid)

        # Assert
        assert result is None
        assert mock_get.call_count == self.client.retry_count

    @patch('requests.get')
    def test_fetch_tender_details_missing_data_key(self, mock_get):
        """Test handling response where 'data' key is missing."""
        # Arrange
        tender_uuid = "a1b2c3d4e5f67890a1b2c3d4e5f67890"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"not_data": {"id": tender_uuid}} # Missing 'data'
        mock_get.return_value = mock_response

        # Act
        result = self.client.fetch_tender_details(tender_uuid)

        # Assert
        assert result is None # Should return None as 'data' is missing
        # It should only be called once because the request succeeded but content was wrong
        assert mock_get.call_count == 1

    def test_fetch_tender_details_empty_uuid(self):
        """Test calling fetch_tender_details with an empty UUID."""
        # Act
        result = self.client.fetch_tender_details("")

        # Assert
        assert result is None