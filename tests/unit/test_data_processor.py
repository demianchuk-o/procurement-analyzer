from datetime import datetime, timezone
from unittest.mock import MagicMock, call, ANY, patch

import pytest

from models import Tender, TenderChange, Bid, BidChange, Award, Complaint, TenderDocument  # Add other models as needed
from repositories.tender_repository import TenderRepository
from services.data_processor import DataProcessor
from schemas.tender_schema import TenderSchema
from schemas.bid_schema import BidSchema
from schemas.award_schema import AwardSchema
from schemas.complaint_schema import ComplaintSchema
from schemas.tender_document_schema import TenderDocumentSchema



class MockModel:
    """Base mock class for all entities"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'default-id')
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.bids = kwargs.get('bids', [])
        self.awards = kwargs.get('awards', [])
        self.documents = kwargs.get('documents', [])
        self.complaints = kwargs.get('complaints', [])


class MockTender(MockModel):
    """Mock Tender with relationships"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Relationships are handled by base MockModel


class MockBid(MockModel):
    """Mock Bid entity"""
    pass


class MockAward(MockModel):
    """Mock Award entity"""
    pass


class MockTenderDocument(MockModel):
    """Mock TenderDocument entity"""
    pass


class MockComplaint(MockModel):
    """Mock Complaint entity"""
    pass


class MockTenderChange(MockModel):
    """Mock change record"""
    pass


class MockBidChange(MockModel):
    """Mock change record"""
    pass


# Example legacy data fixtures (can be expanded)
@pytest.fixture
def sample_legacy_details_new():
    # Represents data for a completely new tender
    return {
        "id": "tender-uuid-new",
        "date": "2025-01-01T10:00:00+02:00",
        "dateModified": "2025-01-01T10:00:00+02:00",
        "title": "New Tender Title",
        "value": {"amount": 1000.0},
        "status": "active.tendering",
        "enquiryPeriod": {"startDate": "2025-01-01T00:00:00Z", "endDate": "2025-01-02T00:00:00Z"},
        "tenderPeriod": {"startDate": "2025-01-03T00:00:00Z", "endDate": "2025-01-04T00:00:00Z"},
        "auctionPeriod": {"startDate": "2025-01-05T00:00:00Z", "endDate": "2025-01-06T00:00:00Z"},
        "awardPeriod": {"startDate": "2025-01-07T00:00:00Z", "endDate": "2025-01-08T00:00:00Z"},
        "documents": [],
        "bids": [
            {
                "id": "bid-uuid-1",
                "date": "2025-01-05T11:00:00Z",
                "status": "active",
                "value": {"amount": 950.0},
                "tenderers": [{"identifier": {"id": "bidder-1", "legalName": "Bidder One"}}]
            }
        ],
        "awards": [],
        "complaints": []
    }


@pytest.fixture
def sample_legacy_details_update():
    # Represents data for updating an existing tender
    return {
        "id": "tender-uuid-existing",
        "date": "2025-01-01T10:00:00+02:00",
        "dateModified": "2025-01-10T15:00:00Z", # Newer date
        "title": "Updated Tender Title", # Changed
        "value": {"amount": 1200.0}, # Changed
        "status": "active.qualification", # Changed
        "enquiryPeriod": {"startDate": "2025-01-01T00:00:00Z", "endDate": "2025-01-02T00:00:00Z"},
        "tenderPeriod": {"startDate": "2025-01-03T00:00:00Z", "endDate": "2025-01-04T00:00:00Z"},
        "auctionPeriod": {"startDate": "2025-01-05T00:00:00Z", "endDate": "2025-01-06T00:00:00Z"},
        "awardPeriod": {"startDate": "2025-01-07T00:00:00Z", "endDate": "2025-01-08T00:00:00Z"},
        "documents": [],
        "bids": [
            {
                "id": "bid-uuid-existing-1", # Existing bid
                "date": "2025-01-05T11:00:00Z",
                "status": "active", # No status change
                "value": {"amount": 980.0}, # Value changed
                "tenderers": [{"identifier": {"id": "bidder-1", "legalName": "Bidder One"}}]
            },
            { # New Bid
                "id": "bid-uuid-new-2",
                "date": "2025-01-09T11:00:00Z",
                "status": "active",
                "value": {"amount": 1100.0},
                "tenderers": [{"identifier": {"id": "bidder-2", "legalName": "Bidder Two"}}]
            }
        ],
        "awards": [],
        "complaints": []
    }


@pytest.fixture
def sample_legacy_details_deleted_bid():
    return {
        "id": "tender-uuid-existing",
        "date": "2025-01-01T10:00:00+02:00",
        "dateModified": "2025-01-11T10:00:00Z", # Newer date
        "title": "Updated Tender Title",
        "value": {"amount": 1200.0},
        "status": "active.qualification",
        "enquiryPeriod": {"startDate": "2025-01-01T00:00:00Z", "endDate": "2025-01-02T00:00:00Z"},
        "tenderPeriod": {"startDate": "2025-01-03T00:00:00Z", "endDate": "2025-01-04T00:00:00Z"},
        "auctionPeriod": {"startDate": "2025-01-05T00:00:00Z", "endDate": "2025-01-06T00:00:00Z"},
        "awardPeriod": {"startDate": "2025-01-07T00:00:00Z", "endDate": "2025-01-08T00:00:00Z"},
        "documents": [],
        "bids": [
            {
                "id": "bid-uuid-existing-1", # Existing bid marked as deleted
                "status": "deleted",
                
            }
        ],
        "awards": [],
        "complaints": []
    }


@patch('services.data_processor.analyze_complaint_and_update_score')
class TestDataProcessor:

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks used in most tests"""
        self.mock_repo = MagicMock(spec=TenderRepository)
        self.processor = DataProcessor(tender_repo=self.mock_repo)

        self.processor.legacy_client = MagicMock()

        self.processor.tender_schema = TenderSchema()
        self.processor.tender_document_schema = TenderDocumentSchema()
        self.processor.bid_schema = BidSchema()
        self.processor.award_schema = AwardSchema()
        self.processor.complaint_schema = ComplaintSchema()

    def test_process_tender_data_new_tender(self, mock_analyze_task, sample_legacy_details_new):
        """Verify processing a completely new tender."""
        tender_uuid = sample_legacy_details_new['id']
        tender_ocid = "ocid-new"
        
        date_modified_from_discovery = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        gc_id = 1

        # Arrange
        self.mock_repo.get_tender_with_relations.return_value = None
        self.processor.legacy_client.fetch_tender_details.return_value = sample_legacy_details_new

        # Act
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid,
            tender_ocid=tender_ocid,
            date_modified_utc=date_modified_from_discovery,
            general_classifier_id=gc_id
        )

        # Assert
        assert result is True
        self.processor.legacy_client.fetch_tender_details.assert_called_once_with(tender_uuid)
        self.mock_repo.get_tender_with_relations.assert_called_once_with(tender_uuid)

        added_entities = [args[0] for args, kwargs in self.mock_repo.add_entity.call_args_list]

        added_tender = next((obj for obj in added_entities if isinstance(obj, Tender)), None)
        assert added_tender is not None
        assert added_tender.id == tender_uuid
        assert added_tender.ocid == tender_ocid
        assert added_tender.title == "New Tender Title"
        assert added_tender.value_amount == 1000.0
        assert added_tender.status == "active.tendering"
        assert added_tender.date_modified == date_modified_from_discovery  # Should use the one from discovery
        assert added_tender.general_classifier_id == gc_id

        assert added_tender.date_created == datetime(2025, 1, 1, 8, 0, 0,
                                                     tzinfo=timezone.utc)  # from "date" field, converted

        added_bid = next((obj for obj in added_entities if isinstance(obj, Bid)), None)
        assert added_bid is not None
        assert added_bid.id == "bid-uuid-1"
        assert added_bid.status == "active"
        assert added_bid.value_amount == 950.0
        assert added_bid.tender_id == tender_uuid

        assert self.mock_repo.flush.call_count >= 1  # At least once for tender, then for related
        self.mock_repo.commit.assert_called_once()
        self.mock_repo.rollback.assert_not_called()

        assert not any(
            isinstance(args[0], TenderChange) for args, kwargs in self.mock_repo.record_change.call_args_list)
        assert not any(isinstance(args[0], BidChange) for args, kwargs in self.mock_repo.record_change.call_args_list)
        mock_analyze_task.apply_async.assert_not_called()  # No new complaints in this data

    def test_process_tender_data_update_tender(self, mock_analyze_task, sample_legacy_details_update):
        """Verify processing an update to an existing tender and its related bid."""
        tender_uuid = sample_legacy_details_update['id']
        tender_ocid = "ocid-existing"
        date_modified_from_discovery = datetime(2025, 1, 10, 15, 0, 0, tzinfo=timezone.utc)
        gc_id = 1

        # Arrange
        mock_existing_bid = MockBid(
            id="bid-uuid-existing-1",
            tender_id=tender_uuid,
            date=datetime(2025, 1, 5, 11, 0, 0, tzinfo=timezone.utc),
            status="active",
            value_amount=950.0,  # Old value
            tenderer_id="bidder-1",
            tenderer_legal_name="Bidder One"
        )
        mock_existing_tender = MockTender(
            id=tender_uuid,
            ocid=tender_ocid,
            date_modified=datetime(2025, 1, 8, 12, 0, 0, tzinfo=timezone.utc),  # Older date in DB
            title="Old Tender Title",
            value_amount=1000.0,
            status="active.tendering",
            general_classifier_id=gc_id,
            bids=[mock_existing_bid],
            awards=[], documents=[], complaints=[]
        )
        self.mock_repo.get_tender_with_relations.return_value = mock_existing_tender
        self.processor.legacy_client.fetch_tender_details.return_value = sample_legacy_details_update

        # Act
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid,
            tender_ocid=tender_ocid,
            date_modified_utc=date_modified_from_discovery,
            general_classifier_id=gc_id
        )

        # Assert
        assert result is True
        self.processor.legacy_client.fetch_tender_details.assert_called_once_with(tender_uuid)
        self.mock_repo.get_tender_with_relations.assert_called_once_with(tender_uuid)

        assert mock_existing_tender.title == "Updated Tender Title"
        assert mock_existing_tender.value_amount == 1200.0
        assert mock_existing_tender.status == "active.qualification"
        assert mock_existing_tender.date_modified == date_modified_from_discovery
        assert mock_existing_tender.general_classifier_id == gc_id 

        assert mock_existing_bid.value_amount == 980.0
        assert mock_existing_bid.status == "active"

        recorded_changes = [args[0] for args, kwargs in self.mock_repo.record_change.call_args_list]
        tender_changes_added = [obj for obj in recorded_changes if isinstance(obj, TenderChange)]


        assert len(tender_changes_added) == 3

        title_change = next(tc for tc in tender_changes_added if tc.field_name == 'title')
        assert title_change.old_value == "Old Tender Title"
        assert title_change.new_value == "Updated Tender Title"
        assert title_change.tender_id == tender_uuid
        assert title_change.change_date == date_modified_from_discovery

        bid_changes_added = [obj for obj in recorded_changes if isinstance(obj, BidChange)]
        assert len(bid_changes_added) == 1
        value_change = bid_changes_added[0]
        assert value_change.field_name == 'value_amount'
        assert value_change.old_value == "950.00"
        assert value_change.new_value == "980.00"
        assert value_change.bid_id == "bid-uuid-existing-1"
        assert value_change.change_date == date_modified_from_discovery


        added_entities = [args[0] for args, kwargs in self.mock_repo.add_entity.call_args_list]
        new_bids_added = [obj for obj in added_entities if isinstance(obj, Bid) and obj.id == "bid-uuid-new-2"]
        assert len(new_bids_added) == 1
        assert new_bids_added[0].tenderer_legal_name == "Bidder Two"
        assert new_bids_added[0].tender_id == tender_uuid

        self.mock_repo.commit.assert_called_once()
        self.mock_repo.rollback.assert_not_called()
        mock_analyze_task.apply_async.assert_not_called()

    def test_process_tender_data_deleted_bid(self, mock_analyze_task, sample_legacy_details_deleted_bid):
        """Verify processing a tender where a bid is now marked as deleted."""
        tender_uuid = sample_legacy_details_deleted_bid['id']
        tender_ocid = "ocid-existing"
        date_modified_from_discovery = datetime(2025, 1, 11, 10, 0, 0, tzinfo=timezone.utc)
        gc_id = 1

        # Arrange
        mock_existing_bid = MockBid(
            id="bid-uuid-existing-1",
            tender_id=tender_uuid,
            status="active",  # Old status
            value_amount=980.0  # Previous value
        )
        mock_existing_tender = MockTender(
            id=tender_uuid,
            ocid=tender_ocid,
            date_modified=datetime(2025, 1, 10, 15, 0, 0, tzinfo=timezone.utc),  # Older date
            title="Updated Tender Title",
            value_amount=1200.0,
            status="active.qualification",
            general_classifier_id=gc_id,
            bids=[mock_existing_bid],
            awards=[], documents=[], complaints=[]
        )
        self.mock_repo.get_tender_with_relations.return_value = mock_existing_tender
        self.processor.legacy_client.fetch_tender_details.return_value = sample_legacy_details_deleted_bid

        # Act
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid,
            tender_ocid=tender_ocid,
            date_modified_utc=date_modified_from_discovery,
            general_classifier_id=gc_id
        )

        # Assert
        assert result is True
        self.processor.legacy_client.fetch_tender_details.assert_called_once_with(tender_uuid)


        assert mock_existing_bid.status == "deleted"


        recorded_changes = [args[0] for args, kwargs in self.mock_repo.record_change.call_args_list]
        bid_changes_added = [obj for obj in recorded_changes if
                             isinstance(obj, BidChange) and obj.bid_id == "bid-uuid-existing-1"]

        assert len(bid_changes_added) == 1
        status_change = bid_changes_added[0]
        assert status_change.field_name == 'status'
        assert status_change.old_value == "active"
        assert status_change.new_value == "deleted"
        assert status_change.change_date == date_modified_from_discovery

        assert mock_existing_tender.date_modified == date_modified_from_discovery

        self.mock_repo.commit.assert_called_once()
        mock_analyze_task.apply_async.assert_not_called()

    def test_process_tender_data_legacy_fetch_failure(self, mock_analyze_task):
        """Test behavior when legacy client fails to fetch details."""
        tender_uuid = "tender-uuid-fetch-fail"
        tender_ocid = "ocid-fetch-fail"
        date_modified = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        gc_id = 1

        # Arrange
        self.processor.legacy_client.fetch_tender_details.return_value = None

        # Act
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid,
            tender_ocid=tender_ocid,
            date_modified_utc=date_modified,
            general_classifier_id=gc_id
        )

        # Assert
        assert result is False
        self.processor.legacy_client.fetch_tender_details.assert_called_once_with(tender_uuid)
        self.mock_repo.get_tender_with_relations.assert_not_called()
        self.mock_repo.add_entity.assert_not_called()
        self.mock_repo.commit.assert_not_called()
        self.mock_repo.rollback.assert_called_once()
        mock_analyze_task.apply_async.assert_not_called()

    def test_process_tender_data_schema_load_failure(self, mock_analyze_task):
        """Test failure when legacy_details cannot be loaded by the schema."""
        tender_uuid = "tender-uuid-bad-schema"
        tender_ocid = "ocid-bad-schema"
        date_modified = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        gc_id = 1
        bad_legacy_details = {"id": tender_uuid, "dateModified": "invalid-date-format"}  # Invalid data for schema

        # Arrange
        self.processor.legacy_client.fetch_tender_details.return_value = bad_legacy_details

        # Act
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid,
            tender_ocid=tender_ocid,
            date_modified_utc=date_modified,
            general_classifier_id=gc_id
        )

        # Assert
        assert result is False  # Schema load failure should lead to False return
        self.processor.legacy_client.fetch_tender_details.assert_called_once_with(tender_uuid)

        self.mock_repo.get_tender_with_relations.assert_not_called()
        self.mock_repo.add_entity.assert_not_called()
        self.mock_repo.commit.assert_not_called()
        self.mock_repo.rollback.assert_called_once()
        mock_analyze_task.apply_async.assert_not_called()

    def test_process_tender_data_id_mismatch(self, mock_analyze_task, sample_legacy_details_new):
        """Test failure when legacy_details ID doesn't match expected UUID."""
        tender_uuid_param = "different-uuid-entirely"
        tender_ocid = "ocid-mismatch"
        date_modified = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        gc_id = 1

        # Arrange
        self.processor.legacy_client.fetch_tender_details.return_value = sample_legacy_details_new

        # Act
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid_param,
            tender_ocid=tender_ocid,
            date_modified_utc=date_modified,
            general_classifier_id=gc_id
        )

        # Assert
        assert result is False  # ID mismatch should lead to False return
        self.processor.legacy_client.fetch_tender_details.assert_called_once_with(tender_uuid_param)

        self.mock_repo.get_tender_with_relations.assert_not_called()
        self.mock_repo.add_entity.assert_not_called()
        self.mock_repo.commit.assert_not_called()
        self.mock_repo.rollback.assert_called_once()  # Rollback due to the error path
        mock_analyze_task.apply_async.assert_not_called()

    def test_process_tender_data_updates_general_classifier_id(self, mock_analyze_task, sample_legacy_details_update):
        """Verify general_classifier_id is updated and a change is recorded."""
        tender_uuid = sample_legacy_details_update['id']
        tender_ocid = "ocid-existing"
        date_modified_from_discovery = datetime(2025, 1, 10, 15, 0, 0, tzinfo=timezone.utc)
        old_gc_id = 1
        new_gc_id = 2

        # Arrange
        mock_existing_tender = MockTender(
            id=tender_uuid,
            ocid=tender_ocid,
            date_modified=datetime(2025, 1, 8, 12, 0, 0, tzinfo=timezone.utc),
            title="Old Tender Title",
            value_amount=1000.0,
            status="active.tendering",
            general_classifier_id=old_gc_id,  # Old GC ID
            bids=[], awards=[], documents=[], complaints=[]
        )
        self.mock_repo.get_tender_with_relations.return_value = mock_existing_tender
        self.processor.legacy_client.fetch_tender_details.return_value = sample_legacy_details_update

        # Act
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid,
            tender_ocid=tender_ocid,
            date_modified_utc=date_modified_from_discovery,
            general_classifier_id=new_gc_id
        )

        # Assert
        assert result is True
        assert mock_existing_tender.general_classifier_id == new_gc_id  # Check the ID was updated

        recorded_changes = [args[0] for args, kwargs in self.mock_repo.record_change.call_args_list]
        gc_id_change = next((tc for tc in recorded_changes if
                             isinstance(tc, TenderChange) and tc.field_name == 'general_classifier_id'), None)

        assert gc_id_change is not None
        assert gc_id_change.old_value == str(old_gc_id)
        assert gc_id_change.new_value == str(new_gc_id)
        assert gc_id_change.tender_id == tender_uuid
        assert gc_id_change.change_date == date_modified_from_discovery
        self.mock_repo.commit.assert_called_once()