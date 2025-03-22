from unittest.mock import patch, Mock

import requests

from api.prozorro_client import ProzorroClient


class TestProzorroClient:

    def setup_method(self) -> None:
        self.client = ProzorroClient(retry_count=2, retry_delay=0)

    @patch('requests.get')
    def test_fetch_tenders_page_success(self, mock_get):
        """Test the successful fetch of tender's page"""

        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "tender-1", "dateModified": "2025-01-01T12:00:00Z"}
            ],
            "next_page": {"offset": "next-page-offset"}
        }
        mock_get.return_value = mock_response

        # Act
        result = self.client.fetch_tenders_page(offset="some-offset", limit=10)

        # Assert
        assert result is not None
        assert "data" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "tender-1"

        mock_get.assert_called_once_with(
            ProzorroClient.BASE_URL,
            params={"offset": "some-offset", "limit": 10 },
            timeout=5
        )

    @patch('requests.get')
    def test_fetch_tenders_page_http_error(self, mock_get):
        """Test handling of HTTP error response"""

        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Act
        result = self.client.fetch_tenders_page(offset="some-offset", limit=10)

        # Assert
        assert result is None
        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_fetch_tenders_page_exception(self, mock_get):
        """Test handling of exception during request"""

        # Arrange
        mock_get.side_effect = requests.RequestException

        # Act
        result = self.client.fetch_tenders_page(offset="some-offset", limit=10)

        # Assert
        assert result is None
        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_fetch_tender_details_success(self, mock_get):
        """Test the successful fetch of tender details"""

        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "id": "tender-1",
                "title": "Tender 1",
                "value": {"amount": 1000, "currency": "UAH"},
                "dateModified": "2025-01-01T12:00:00Z"
            }
        }
        mock_get.return_value = mock_response

        # Act
        result = self.client.fetch_tender_details("tender-1")

        # Assert
        assert result is not None
        assert result["id"] == "tender-1"
        assert result["title"] == "Tender 1"
        assert result["value"]["amount"] == 1000
        assert result["value"]["currency"] == "UAH"
        assert result["dateModified"] == "2025-01-01T12:00:00Z"

        mock_get.assert_called_once_with(
            f"{ProzorroClient.BASE_URL}/tender-1",
            timeout=5
        )

    @patch('requests.get')
    def test_fetch_tender_details_empty_on_error(self, mock_get):
        """Test that empty dict is returned on error"""

        # Arrange
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        # Act
        result = self.client.fetch_tender_details("tender-1")

        # Assert
        assert result == {}
        assert mock_get.call_count == 2

    @patch('time.sleep')
    @patch.object(ProzorroClient, 'fetch_tenders_page')
    def test_fetch_all_tenders_pagination(self, mock_fetch_page, mock_sleep):
        """Test pagination of fetch_all_tenders"""
        # Arrange
        # Three pages with one element each
        mock_fetch_page.side_effect = [
            # First page
            {
                "data": [{"id": "tender-1", "dateModified": "2025-01-01T12:00:00Z"}],
                "next_page": {"offset": "page-2"}
            },
            # Second page
            {
                "data": [{"id": "tender-2", "dateModified": "2025-01-02T12:00:00Z"}],
                "next_page": {"offset": "page-3"}
            },
            # Third page (last)
            {
                "data": [{"id": "tender-3", "dateModified": "2025-01-03T12:00:00Z"}],
                "next_page": None
            }
        ]

        # Act
        result = self.client.fetch_all_tenders(start_offset="page-1")

        # Assert
        assert len(result) == 3
        assert result[0]["id"] == "tender-1"
        assert result[1]["id"] == "tender-2"
        assert result[2]["id"] == "tender-3"
        assert mock_fetch_page.call_count == 3

    @patch.object(ProzorroClient, 'fetch_tenders_page')
    def fetch_all_tenders_empty_response(self, mock_fetch_page):
        """Test handling of empty response in fetch_all_tenders"""
        # Arrange
        mock_fetch_page.return_value = None

        # Act
        result = self.client.fetch_all_tenders()

        # Assert
        assert result == []
        assert mock_fetch_page.assert_called_once()