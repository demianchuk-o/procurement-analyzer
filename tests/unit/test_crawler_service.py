from datetime import datetime, timezone
from unittest.mock import MagicMock, call

import pytest

from repositories.tender_repository import TenderRepository
from services.crawler_service import CrawlerService


class TestCrawlerService:

    @pytest.fixture
    def mock_tender_repo(self):
        return MagicMock(spec=TenderRepository)

    @pytest.fixture
    def mock_discovery_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_legacy_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_data_processor(self):
        return MagicMock()

    @pytest.fixture
    def crawler_service(self, mock_tender_repo, mock_discovery_client, mock_legacy_client, mock_data_processor):
        service = CrawlerService(tender_repo=mock_tender_repo)
        service.discovery_client = mock_discovery_client
        service.legacy_client = mock_legacy_client
        service.data_processor = mock_data_processor
        return service

    def test_sync_single_tender_success(self, crawler_service, mock_tender_repo, mock_discovery_client, mock_legacy_client, mock_data_processor):
        """Test successful sync of a single tender."""
        # Arrange
        mock_discovery_client.fetch_tender_bridge_info.return_value = {
            'id': 'tender_uuid',
            'dateModified': datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            'generalClassifier': {'scheme': 'scheme', 'description': 'description'}
        }
        mock_tender_repo.get_by_id.return_value = None
        mock_tender_repo.find_general_classifier.return_value = None
        mock_tender_repo.create_general_classifier.return_value = MagicMock(id=1)
        mock_legacy_client.fetch_tender_details.return_value = {'key': 'value'}
        mock_data_processor.process_tender_data.return_value = True

        # Act
        result = crawler_service.sync_single_tender('tender_ocid')

        # Assert
        assert result is True
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with('tender_ocid')
        mock_tender_repo.get_by_id.assert_called_once_with('tender_uuid')
        mock_tender_repo.find_general_classifier.assert_called_once_with(scheme='scheme', description='description')
        mock_tender_repo.create_general_classifier.assert_called_once_with(scheme='scheme', description='description')
        mock_legacy_client.fetch_tender_details.assert_called_once_with('tender_uuid')
        mock_data_processor.process_tender_data.assert_called_once_with(
            tender_uuid='tender_uuid',
            tender_ocid='tender_ocid',
            date_modified_utc=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            general_classifier_id=1,
            legacy_details={'key': 'value'}
        )
        mock_tender_repo.commit.assert_called_once()

    def test_sync_single_tender_no_bridge_info(self, crawler_service, mock_discovery_client):
        """Test when discovery client returns no bridge info."""
        # Arrange
        mock_discovery_client.fetch_tender_bridge_info.return_value = None

        # Act
        result = crawler_service.sync_single_tender('tender_ocid')

        # Assert
        assert result is False
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with('tender_ocid')

    def test_sync_single_tender_missing_data_in_bridge_info(self, crawler_service, mock_discovery_client):
        """Test when bridge info is missing UUID or dateModified."""
        # Arrange
        mock_discovery_client.fetch_tender_bridge_info.return_value = {}

        # Act
        result = crawler_service.sync_single_tender('tender_ocid')

        # Assert
        assert result is False
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with('tender_ocid')

    def test_sync_single_tender_tender_unchanged(self, crawler_service, mock_tender_repo, mock_discovery_client):
        """Test when the tender has not been modified since the last sync."""
        # Arrange
        mock_discovery_client.fetch_tender_bridge_info.return_value = {
            'id': 'tender_uuid',
            'dateModified': datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            'generalClassifier': {'scheme': 'scheme', 'description': 'description'}
        }
        mock_tender_repo.get_by_id.return_value = MagicMock(date_modified=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc))

        # Act
        result = crawler_service.sync_single_tender('tender_ocid')

        # Assert
        assert result is True
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with('tender_ocid')
        mock_tender_repo.get_by_id.assert_called_once_with('tender_uuid')

    def test_sync_single_tender_legacy_details_fetch_failure(self, crawler_service, mock_tender_repo, mock_discovery_client, mock_legacy_client):
        """Test when fetching legacy details fails."""
        # Arrange
        mock_discovery_client.fetch_tender_bridge_info.return_value = {
            'id': 'tender_uuid',
            'dateModified': datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            'generalClassifier': {'scheme': 'scheme', 'description': 'description'}
        }
        mock_tender_repo.get_by_id.return_value = None
        mock_tender_repo.find_general_classifier.return_value = None
        mock_tender_repo.create_general_classifier.return_value = MagicMock(id=1)
        mock_legacy_client.fetch_tender_details.return_value = None

        # Act
        result = crawler_service.sync_single_tender('tender_ocid')

        # Assert
        assert result is False
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with('tender_ocid')
        mock_tender_repo.get_by_id.assert_called_once_with('tender_uuid')
        mock_tender_repo.find_general_classifier.assert_called_once_with(scheme='scheme', description='description')
        mock_tender_repo.create_general_classifier.assert_called_once_with(scheme='scheme', description='description')
        mock_legacy_client.fetch_tender_details.assert_called_once_with('tender_uuid')
        mock_tender_repo.rollback.assert_called_once()

    def test_sync_single_tender_data_processor_failure(self, crawler_service, mock_tender_repo, mock_discovery_client, mock_legacy_client, mock_data_processor):
        """Test when the data processor fails."""
        # Arrange
        mock_discovery_client.fetch_tender_bridge_info.return_value = {
            'id': 'tender_uuid',
            'dateModified': datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            'generalClassifier': {'scheme': 'scheme', 'description': 'description'}
        }
        mock_tender_repo.get_by_id.return_value = None
        mock_tender_repo.find_general_classifier.return_value = None
        mock_tender_repo.create_general_classifier.return_value = MagicMock(id=1)
        mock_legacy_client.fetch_tender_details.return_value = {'key': 'value'}
        mock_data_processor.process_tender_data.return_value = False

        # Act
        result = crawler_service.sync_single_tender('tender_ocid')

        # Assert
        assert result is False
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with('tender_ocid')
        mock_tender_repo.get_by_id.assert_called_once_with('tender_uuid')
        mock_tender_repo.find_general_classifier.assert_called_once_with(scheme='scheme', description='description')
        mock_tender_repo.create_general_classifier.assert_called_once_with(scheme='scheme', description='description')
        mock_legacy_client.fetch_tender_details.assert_called_once_with('tender_uuid')
        mock_data_processor.process_tender_data.assert_called_once_with(
            tender_uuid='tender_uuid',
            tender_ocid='tender_ocid',
            date_modified_utc=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            general_classifier_id=1,
            legacy_details={'key': 'value'}
        )

    def test_sync_subscribed_tenders_success(self, crawler_service, mock_tender_repo):
        """Test successful sync of subscribed tenders."""
        # Arrange
        mock_tender_repo.get_subscribed_tender_ocids.return_value = ['tender_ocid_1', 'tender_ocid_2']
        crawler_service.sync_single_tender = MagicMock(return_value=True)

        # Act
        result = crawler_service.sync_subscribed_tenders()

        # Assert
        assert result == 2
        mock_tender_repo.get_subscribed_tender_ocids.assert_called_once()
        crawler_service.sync_single_tender.assert_has_calls([call('tender_ocid_1'), call('tender_ocid_2')])

    def test_sync_subscribed_tenders_error(self, crawler_service, mock_tender_repo):
        """Test when an error occurs during the sync of subscribed tenders."""
        # Arrange
        mock_tender_repo.get_subscribed_tender_ocids.return_value = ['tender_ocid_1', 'tender_ocid_2']
        crawler_service.sync_single_tender = MagicMock(side_effect=[True, Exception('Sync error')])

        # Act
        result = crawler_service.sync_subscribed_tenders()

        # Assert
        assert result == 1
        mock_tender_repo.get_subscribed_tender_ocids.assert_called_once()
        assert crawler_service.sync_single_tender.call_count == 2

    def test_crawl_tenders_success(self, crawler_service, mock_discovery_client):
        """Test successful crawl of tenders."""
        # Arrange
        mock_discovery_client.fetch_search_page_tender_ids.return_value = ['tender_ocid_1', 'tender_ocid_2']
        crawler_service.sync_single_tender = MagicMock(return_value=True)

        # Act
        result = crawler_service.crawl_tenders(pages_to_crawl=1)

        # Assert
        assert result == 2
        mock_discovery_client.fetch_search_page_tender_ids.assert_called_once_with(page=0)
        crawler_service.sync_single_tender.assert_has_calls([call('tender_ocid_1'), call('tender_ocid_2')])

    def test_crawl_tenders_no_tenders_found(self, crawler_service, mock_discovery_client):
        """Test when no tenders are found on a search page."""
        # Arrange
        mock_discovery_client.fetch_search_page_tender_ids.return_value = []

        # Act
        result = crawler_service.crawl_tenders(pages_to_crawl=1)

        # Assert
        assert result == 0
        mock_discovery_client.fetch_search_page_tender_ids.assert_called_once_with(page=0)

    def test_crawl_tenders_discovery_client_failure(self, crawler_service, mock_discovery_client):
        """Test when the discovery client fails to fetch a search page."""
        # Arrange
        mock_discovery_client.fetch_search_page_tender_ids.return_value = None

        # Act
        result = crawler_service.crawl_tenders(pages_to_crawl=1)

        # Assert
        assert result == 0
        mock_discovery_client.fetch_search_page_tender_ids.assert_called_once_with(page=0)

    def test_crawl_tenders_sync_single_tender_failure(self, crawler_service, mock_discovery_client):
        """Test when syncing a single tender fails during the crawl."""
        # Arrange
        mock_discovery_client.fetch_search_page_tender_ids.return_value = ['tender_ocid_1', 'tender_ocid_2']
        crawler_service.sync_single_tender = MagicMock(side_effect=[True, False])

        # Act
        result = crawler_service.crawl_tenders(pages_to_crawl=1)

        # Assert
        assert result == 1
        mock_discovery_client.fetch_search_page_tender_ids.assert_called_once_with(page=0)
        assert crawler_service.sync_single_tender.call_count == 2

    def test_find_or_create_general_classifier_existing(self, crawler_service, mock_tender_repo):
        """Test when a general classifier already exists."""
        # Arrange
        mock_tender_repo.find_general_classifier.return_value = MagicMock(id=1)

        # Act
        result = crawler_service._find_or_create_general_classifier({'scheme': 'scheme', 'description': 'description'})

        # Assert
        assert result == 1
        mock_tender_repo.find_general_classifier.assert_called_once_with(scheme='scheme', description='description')
        mock_tender_repo.create_general_classifier.assert_not_called()

    def test_find_or_create_general_classifier_new(self, crawler_service, mock_tender_repo):
        """Test when a general classifier needs to be created."""
        # Arrange
        mock_tender_repo.find_general_classifier.return_value = None
        mock_tender_repo.create_general_classifier.return_value = MagicMock(id=2)

        # Act
        result = crawler_service._find_or_create_general_classifier({'scheme': 'scheme', 'description': 'description'})

        # Assert
        assert result == 2
        mock_tender_repo.find_general_classifier.assert_called_once_with(scheme='scheme', description='description')
        mock_tender_repo.create_general_classifier.assert_called_once_with(scheme='scheme', description='description')

    def test_find_or_create_general_classifier_missing_data(self, crawler_service):
        """Test when the classifier data is missing scheme or description."""
        # Arrange & Act
        result = crawler_service._find_or_create_general_classifier({})

        # Assert
        assert result is None