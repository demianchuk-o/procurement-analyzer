from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from repositories.tender_repository import TenderRepository
from services.crawler_service import CrawlerService


@patch('services.crawler_service.process_tender_data_task')
class TestCrawlerService:

    @pytest.fixture
    def mock_tender_repo(self):
        return MagicMock(spec=TenderRepository)

    @pytest.fixture
    def mock_discovery_client(self):
        return MagicMock()

    @pytest.fixture
    def crawler_service(self, mock_tender_repo, mock_discovery_client):
        service = CrawlerService(tender_repo=mock_tender_repo)
        service.discovery_client = mock_discovery_client
        return service

    def test_sync_single_tender_success(self, mock_process_task, crawler_service, mock_tender_repo,
                                        mock_discovery_client):
        """Test successful sync of a single tender that is new or needs update."""
        # Arrange
        tender_ocid = 'tender_ocid_1'
        tender_uuid = 'tender_uuid_1'
        date_modified = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        classifier_data = {'scheme': 'scheme_A', 'description': 'description_A', 'id': 'classifier_id_A'}

        mock_discovery_client.fetch_tender_bridge_info.return_value = {
            'id': tender_uuid,
            'dateModified': date_modified,
            'generalClassifier': classifier_data,
            'tenderID': tender_ocid
        }

        mock_tender_repo.get_short_by_uuid.return_value = None

        # Act
        crawler_service.sync_single_tender(tender_ocid)

        # Assert
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with(tender_ocid)
        mock_tender_repo.get_short_by_uuid.assert_called_once_with(tender_uuid)
        mock_process_task.apply_async.assert_called_once_with(
            args=(tender_uuid, tender_ocid, date_modified, classifier_data),
            queue='default',
            priority=0
        )

    def test_sync_single_tender_no_bridge_info(self, mock_process_task, crawler_service, mock_discovery_client):
        """Test when discovery client returns no bridge info."""
        # Arrange
        tender_ocid = 'tender_ocid_2'
        mock_discovery_client.fetch_tender_bridge_info.return_value = None

        # Act
        crawler_service.sync_single_tender(tender_ocid)

        # Assert
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with(tender_ocid)
        mock_process_task.apply_async.assert_not_called()

    def test_sync_single_tender_missing_data_in_bridge_info(self, mock_process_task, crawler_service,
                                                            mock_discovery_client):
        """Test when bridge info is missing UUID or dateModified."""
        # Arrange
        tender_ocid = 'tender_ocid_3'
        # Missing 'id' and 'dateModified'
        mock_discovery_client.fetch_tender_bridge_info.return_value = {'tenderID': tender_ocid}

        # Act
        crawler_service.sync_single_tender(tender_ocid)

        # Assert
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with(tender_ocid)
        mock_process_task.apply_async.assert_not_called()

    def test_sync_single_tender_tender_unchanged(self, mock_process_task, crawler_service, mock_tender_repo,
                                                 mock_discovery_client):
        """Test when the tender has not been modified since the last sync."""
        # Arrange
        tender_ocid = 'tender_ocid_4'
        tender_uuid = 'tender_uuid_4'
        # Date from bridge is same or older than in DB
        date_modified_in_bridge = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        date_modified_in_db = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        mock_discovery_client.fetch_tender_bridge_info.return_value = {
            'id': tender_uuid,
            'dateModified': date_modified_in_bridge,
            'generalClassifier': {'scheme': 's', 'description': 'd', 'id': 'id'},
            'tenderID': tender_ocid
        }
        mock_tender_repo.get_short_by_uuid.return_value = {
            'date_modified': date_modified_in_db
        }

        # Act
        crawler_service.sync_single_tender(tender_ocid)

        # Assert
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with(tender_ocid)
        mock_tender_repo.get_short_by_uuid.assert_called_once_with(tender_uuid)
        mock_process_task.apply_async.assert_not_called()

    def test_sync_single_tender_older_in_db_triggers_sync(self, mock_process_task, crawler_service, mock_tender_repo,
                                                          mock_discovery_client):
        """Test when the tender in DB is older, sync should be triggered."""
        # Arrange
        tender_ocid = 'tender_ocid_5'
        tender_uuid = 'tender_uuid_5'
        date_modified_in_bridge = datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        date_modified_in_db = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)  # Older
        classifier_data = {'scheme': 's', 'description': 'd', 'id': 'id'}

        mock_discovery_client.fetch_tender_bridge_info.return_value = {
            'id': tender_uuid,
            'dateModified': date_modified_in_bridge,
            'generalClassifier': classifier_data,
            'tenderID': tender_ocid
        }
        mock_tender_repo.get_short_by_uuid.return_value = {
            'date_modified': date_modified_in_db
        }

        # Act
        crawler_service.sync_single_tender(tender_ocid, high_priority=True)

        # Assert
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with(tender_ocid)
        mock_tender_repo.get_short_by_uuid.assert_called_once_with(tender_uuid)
        mock_process_task.apply_async.assert_called_once_with(
            args=(tender_uuid, tender_ocid, date_modified_in_bridge, classifier_data),
            queue='default',
            priority=5  # high_priority = True
        )

    def test_sync_single_tender_schedules_task_for_new_tender(self, mock_process_task, crawler_service,
                                                              mock_tender_repo, mock_discovery_client):
        """Test that task is scheduled for a new tender (not in DB)."""
        # Arrange
        tender_ocid = 'tender_ocid_6'
        tender_uuid = 'tender_uuid_6'
        date_modified = datetime(2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc)
        classifier_data = {'scheme': 's', 'description': 'd', 'id': 'id'}

        mock_discovery_client.fetch_tender_bridge_info.return_value = {
            'id': tender_uuid,
            'dateModified': date_modified,
            'generalClassifier': classifier_data,
            'tenderID': tender_ocid
        }
        mock_tender_repo.get_short_by_uuid.return_value = None  # Tender not in DB

        # Act
        crawler_service.sync_single_tender(tender_ocid)

        # Assert
        mock_discovery_client.fetch_tender_bridge_info.assert_called_once_with(tender_ocid)
        mock_tender_repo.get_short_by_uuid.assert_called_once_with(tender_uuid)
        mock_process_task.apply_async.assert_called_once_with(
            args=(tender_uuid, tender_ocid, date_modified, classifier_data),
            queue='default',
            priority=0
        )

    def test_crawl_tenders_success(self, mock_process_task, crawler_service,
                                   mock_discovery_client):
        """Test successful crawl of tenders."""
        # Arrange
        mock_discovery_client.fetch_search_page_tender_ids.return_value = ['tender_ocid_A', 'tender_ocid_B']

        # avoid calling the actual sync_single_tender method
        crawler_service.sync_single_tender = MagicMock()

        # Act
        result = crawler_service.crawl_tenders(pages_to_crawl=1)

        # Assert
        assert result == 2  # Processed count
        mock_discovery_client.fetch_search_page_tender_ids.assert_called_once_with(page=0)
        crawler_service.sync_single_tender.assert_has_calls([call('tender_ocid_A'), call('tender_ocid_B')])

    def test_crawl_tenders_no_tenders_found(self, mock_process_task, crawler_service, mock_discovery_client):
        """Test when no tenders are found on a search page."""
        # Arrange
        mock_discovery_client.fetch_search_page_tender_ids.return_value = []
        crawler_service.sync_single_tender = MagicMock()

        # Act
        result = crawler_service.crawl_tenders(pages_to_crawl=1)

        # Assert
        assert result == 0
        mock_discovery_client.fetch_search_page_tender_ids.assert_called_once_with(page=0)
        crawler_service.sync_single_tender.assert_not_called()

    def test_crawl_tenders_discovery_client_failure(self, mock_process_task, crawler_service, mock_discovery_client):
        """Test when the discovery client fails to fetch a search page."""
        # Arrange
        mock_discovery_client.fetch_search_page_tender_ids.return_value = None
        crawler_service.sync_single_tender = MagicMock()

        # Act
        result = crawler_service.crawl_tenders(pages_to_crawl=1)

        # Assert
        assert result == 0
        mock_discovery_client.fetch_search_page_tender_ids.assert_called_once_with(page=0)
        crawler_service.sync_single_tender.assert_not_called()

    def test_crawl_tenders_iterates_and_counts_all_found_ocids(self, mock_process_task, crawler_service,
                                                               mock_discovery_client):
        """
        Test that crawl_tenders processes all OCIDs found,
        and processed_count reflects the number of sync attempts.
        """
        # Arrange
        mock_discovery_client.fetch_search_page_tender_ids.return_value = ['tender_ocid_X', 'tender_ocid_Y']
        # mock sync_single_tender to avoid actual processing
        crawler_service.sync_single_tender = MagicMock()

        # Act
        result = crawler_service.crawl_tenders(pages_to_crawl=1)

        # Assert
        assert result == 2  # Should process both OCIDs found
        mock_discovery_client.fetch_search_page_tender_ids.assert_called_once_with(page=0)
        assert crawler_service.sync_single_tender.call_count == 2
        crawler_service.sync_single_tender.assert_has_calls([call('tender_ocid_X'), call('tender_ocid_Y')])

    def test_sync_all_tenders_success(self, mock_process_task, crawler_service, mock_tender_repo):
        """Test syncing all active tenders from the repository."""
        # Arrange
        active_ocids = ['ocid_db_1', 'ocid_db_2']
        mock_tender_repo.get_active_tender_ocids.return_value = active_ocids

        crawler_service.sync_single_tender = MagicMock()

        # Act
        result = crawler_service.sync_all_tenders()

        # Assert
        assert result == len(active_ocids)
        mock_tender_repo.get_active_tender_ocids.assert_called_once()
        crawler_service.sync_single_tender.assert_has_calls(
            [call(ocid) for ocid in active_ocids], any_order=False
        )

    def test_sync_all_tenders_no_active_tenders(self, mock_process_task, crawler_service, mock_tender_repo):
        """Test syncing when no active tenders are in the repository."""
        # Arrange
        mock_tender_repo.get_active_tender_ocids.return_value = []
        crawler_service.sync_single_tender = MagicMock()

        # Act
        result = crawler_service.sync_all_tenders()

        # Assert
        assert result == 0
        mock_tender_repo.get_active_tender_ocids.assert_called_once()
        crawler_service.sync_single_tender.assert_not_called()