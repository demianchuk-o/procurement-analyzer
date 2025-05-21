from datetime import datetime
from unittest.mock import patch, Mock

import pytest
import requests

from api.discovery_prozorro_client import DiscoveryProzorroClient
from schemas.discovery_schema import SearchPageSchema, TenderBridgeInfoSchema


class TestDiscoveryProzorroClient:

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self):
        self.client = DiscoveryProzorroClient(retry_count=2, retry_delay=0)

        self.client.search_page_schema = SearchPageSchema()
        self.client.bridge_info_schema = TenderBridgeInfoSchema()

    @patch('api.discovery_prozorro_client.requests.request')
    def test_fetch_search_page_tender_ids_success_page_0(self, mock_request):
        """Test fetching tender IDs from search page 0 successfully."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "page": 0, "per_page": 20, "total": 5000,
            "data": [
                {"tenderID": "UA-2024-02-01-000001-a", "title": "Tender A"},
                {"tenderID": "UA-2024-02-01-000002-b", "title": "Tender B"}
            ]
        }
        mock_request.return_value = mock_response

        # Act
        result = self.client.fetch_search_page_tender_ids(page=0)

        # Assert
        assert result == ["UA-2024-02-01-000001-a", "UA-2024-02-01-000002-b"]
        expected_url = f"{DiscoveryProzorroClient.BASE_URL}{DiscoveryProzorroClient.SEARCH_ENDPOINT}"
        mock_request.assert_called_once_with(
            "POST",
            expected_url,
            params={'page': None}, # Client sets page to None for page 0
            timeout=self.client.timeout
        )

    @patch('api.discovery_prozorro_client.requests.request')
    def test_fetch_search_page_tender_ids_success_page_1(self, mock_request):
        """Test fetching tender IDs from search page 1 successfully."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "page": 1, "per_page": 20, "total": 5000,
            "data": [{"tenderID": "UA-2024-02-01-000003-c"}]
        }
        mock_request.return_value = mock_response

        # Act
        result = self.client.fetch_search_page_tender_ids(page=1)

        # Assert
        assert result == ["UA-2024-02-01-000003-c"]
        expected_url = f"{DiscoveryProzorroClient.BASE_URL}{DiscoveryProzorroClient.SEARCH_ENDPOINT}"
        mock_request.assert_called_once_with(
            "POST",
            expected_url,
            params={"page": 1},
            timeout=self.client.timeout
        )

    @patch('api.discovery_prozorro_client.requests.request')
    def test_fetch_search_page_tender_ids_http_error(self, mock_request):
        """Test search page fetch with HTTP error."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_request.return_value = mock_response

        # Act
        result = self.client.fetch_search_page_tender_ids(page=0)

        # Assert
        assert result is None
        assert mock_request.call_count == self.client.retry_count

    @patch('api.discovery_prozorro_client.requests.request')
    def test_fetch_search_page_tender_ids_request_exception(self, mock_request):
        """Test search page fetch with network error."""
        # Arrange
        mock_request.side_effect = requests.exceptions.RequestException("Connection failed")

        # Act
        result = self.client.fetch_search_page_tender_ids(page=0)

        # Assert
        assert result is None
        assert mock_request.call_count == self.client.retry_count

    @patch('api.discovery_prozorro_client.requests.request')
    def test_fetch_search_page_tender_ids_schema_validation_error(self, mock_request):
        """Test search page fetch with data failing schema validation."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = { # Missing 'tenderID'
             "page": 0, "per_page": 20, "total": 5000,
             "data": [{"title": "Invalid Tender"}]
        }
        mock_request.return_value = mock_response

        # Act
        result = self.client.fetch_search_page_tender_ids(page=0)

        # Assert
        assert result is None # Schema validation error leads to None
        assert mock_request.call_count == 1 # No retries on schema validation error

    def test_fetch_search_page_tender_ids_invalid_page(self):
        """Test calling search page fetch with negative page number."""
        # Act
        result = self.client.fetch_search_page_tender_ids(page=-1)
        # Assert
        assert result is None

    @patch('api.discovery_prozorro_client.requests.request')
    def test_fetch_tender_bridge_info_success(self, mock_request):
        """Test fetching bridge info successfully."""
        # Arrange
        ocid = "UA-2024-01-01-000001-a"
        uuid = "b1b2c3d4e5f67890b1b2c3d4e5f67890"
        date_str = "2024-01-15T10:30:00+02:00"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "id": uuid, "tenderID": ocid, "dateModified": date_str,
            "generalClassifier": {"scheme": "ДК021", "description": "Some Category", "id": "12345678-9"},
            "title": "Some other fields we ignore"
        }
        mock_request.return_value = mock_response

        # Act
        result = self.client.fetch_tender_bridge_info(ocid)

        # Assert
        assert result is not None
        assert result["id"] == uuid
        assert result["tenderID"] == ocid
        assert isinstance(result["dateModified"], datetime)
        expected_dt = datetime.fromisoformat(date_str)
        assert result["dateModified"] == expected_dt
        assert result["generalClassifier"]["scheme"] == "ДК021"

        expected_url = f"{DiscoveryProzorroClient.BASE_URL}{DiscoveryProzorroClient.TENDER_ENDPOINT}{ocid}/"
        mock_request.assert_called_once_with(
            "GET",
            expected_url,
            params=None, # fetch_tender_bridge_info passes None as params to _make_request
            timeout=self.client.timeout
        )

    @patch('api.discovery_prozorro_client.requests.request')
    def test_fetch_tender_bridge_info_http_error(self, mock_request):
        """Test bridge info fetch with HTTP error."""
        # Arrange
        ocid = "UA-2024-01-01-000001-a"
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_request.return_value = mock_response

        # Act
        result = self.client.fetch_tender_bridge_info(ocid)

        # Assert
        assert result is None
        assert mock_request.call_count == self.client.retry_count

    @patch('api.discovery_prozorro_client.requests.request')
    def test_fetch_tender_bridge_info_request_exception(self, mock_request):
        """Test bridge info fetch with network error."""
        # Arrange
        ocid = "UA-2024-01-01-000001-a"
        mock_request.side_effect = requests.exceptions.RequestException("Timeout")

        # Act
        result = self.client.fetch_tender_bridge_info(ocid)

        # Assert
        assert result is None
        assert mock_request.call_count == self.client.retry_count

    @patch('api.discovery_prozorro_client.requests.request')
    def test_fetch_tender_bridge_info_schema_validation_error(self, mock_request):
        """Test bridge info fetch with data failing schema validation."""
        # Arrange
        ocid = "UA-2024-01-01-000001-a"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = { # Missing 'id' (UUID)
            "tenderID": ocid, "dateModified": "2024-01-15T10:30:00+02:00",
            "generalClassifier": {"scheme": "ДК021", "description": "Some Category"}
        }
        mock_request.return_value = mock_response

        # Act
        result = self.client.fetch_tender_bridge_info(ocid)

        # Assert
        assert result is None # Schema validation error leads to None
        assert mock_request.call_count == 1 # No retries on schema validation error

    def test_fetch_tender_bridge_info_empty_ocid(self):
        """Test calling bridge info fetch with empty OCID."""
        # Act
        result = self.client.fetch_tender_bridge_info("")
        # Assert
        assert result is None