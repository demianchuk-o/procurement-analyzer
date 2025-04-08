import pytest
from unittest.mock import MagicMock, call, ANY # ANY helps match objects without exact equality
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from repositories.tender_repository import TenderRepository
# Import the class to test and necessary models/schemas
from services.data_processor import DataProcessor
from models import Tender, TenderChange, Bid, BidChange # Add other models as needed

class MockModel:
    """Base mock class for all entities"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'default-id')
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockTender(MockModel):
    """Mock Tender with relationships"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bids = kwargs.get('bids', [])
        self.awards = kwargs.get('awards', [])
        self.documents = kwargs.get('documents', [])
        self.complaints = kwargs.get('complaints', [])

class MockBid(MockModel):
    """Mock Bid entity"""
    pass

class MockAward(MockModel):
    """Mock Award entity"""
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
        "bids": [
            {
                "id": "bid-uuid-1",
                "date": "2025-01-05T11:00:00Z",
                "status": "active",
                "value": {"amount": 950.0},
                "tenderers": [{"identifier": {"id": "bidder-1", "legalName": "Bidder One"}}]
            }
        ]
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
        ]
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
        "bids": [
            {
                "id": "bid-uuid-existing-1", # Existing bid marked as deleted
                "status": "deleted",
                # Other fields might be missing in a real 'deleted' response
            }
        ]
    }


class TestDataProcessor:

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks used in most tests"""
        self.mock_repo = MagicMock(spec=TenderRepository)
        # Instantiate the processor with the mock session
        self.processor = DataProcessor(tender_repo=self.mock_repo)

    def test_process_tender_data_new_tender(self, sample_legacy_details_new):
        """Verify processing a completely new tender."""
        tender_uuid = sample_legacy_details_new['id']
        tender_ocid = "ocid-new"
        date_modified = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc) # from dateModified
        gc_id = 1

        # --- Arrange ---
        self.mock_repo.get_tender_with_relations.return_value = None

        # --- Act ---
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid,
            tender_ocid=tender_ocid,
            date_modified_utc=date_modified,
            general_classifier_id=gc_id,
            legacy_details=sample_legacy_details_new
        )

        # --- Assert ---
        assert result is True
        self.mock_repo.get_tender_with_relations.assert_called_once_with(tender_uuid)

        expected_calls = [
            call(ANY), # Tender object
            call(ANY)  # Bid object
        ]
        self.mock_repo.add_entity.assert_has_calls(expected_calls, any_order=True)

        added_entities = [args[0] for args, kwargs in self.mock_repo.add_entity.call_args_list]
        added_tenders = [obj for obj in added_entities if isinstance(obj, Tender)]

        added_tender = added_tenders[0] if added_tenders else None

        assert added_tender is not None
        assert added_tender.id == tender_uuid
        assert added_tender.ocid == tender_ocid
        assert added_tender.title == "New Tender Title"
        assert added_tender.status == "active.tendering"
        assert added_tender.date_modified == date_modified
        assert added_tender.general_classifier_id == gc_id

        added_bids = [obj for obj in added_entities if isinstance(obj, Bid)]
        added_bid = added_bids[0] if added_bids else None

        assert added_bid is not None
        assert added_bid.id == "bid-uuid-1"
        assert added_bid.status == "active"
        assert added_bid.tender_id == tender_uuid # Check FK set correctly

        # 3. Check session.flush was called (once for tender, once per related sync if new items added)
        #    The exact number might vary slightly based on implementation details,
        #    but it should be called at least once for the main tender.
        assert self.mock_repo.flush.call_count >= 1

        # 4. Ensure NO change records were added for the *new* tender/bid itself
        assert not any(isinstance(args[0], TenderChange) for args, kwargs in self.mock_repo.record_change.call_args_list)
        assert not any(isinstance(args[0], BidChange) for args, kwargs in self.mock_repo.record_change.call_args_list)

    def test_process_tender_data_update_tender(self, sample_legacy_details_update):
        """Verify processing an update to an existing tender and its related bid."""
        tender_uuid = sample_legacy_details_update['id']
        tender_ocid = "ocid-existing"
        date_modified_api = datetime(2025, 1, 10, 15, 0, 0, tzinfo=timezone.utc) # from dateModified
        gc_id = 1

        # --- Arrange ---
        # Mock existing Bid
        mock_existing_bid = MockBid(
            id="bid-uuid-existing-1",
            tender_id=tender_uuid,
            date=datetime(2025, 1, 5, 11, 0, 0, tzinfo=timezone.utc),
            status="active",
            value_amount=950.0, # Old value
            tenderer_id="bidder-1",
            tenderer_legal_name="Bidder One"
        )
        # Mock existing Tender, including the existing bid in its relationship
        mock_existing_tender = MockTender(
            id=tender_uuid,
            ocid=tender_ocid,
            date_modified=datetime(2025, 1, 8, 12, 0, 0, tzinfo=timezone.utc), # Older date
            title="Old Tender Title",
            value_amount=1000.0,
            status="active.tendering",
            general_classifier_id=gc_id,
            bids=[mock_existing_bid] # Link the existing mock bid
        )
        self.mock_repo.get_tender_with_relations.return_value = mock_existing_tender

        # --- Act ---
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid,
            tender_ocid=tender_ocid, # Same OCID
            date_modified_utc=date_modified_api,
            general_classifier_id=gc_id, # Same GC ID
            legacy_details=sample_legacy_details_update
        )

        # --- Assert ---
        assert result is True
        self.mock_repo.get_tender_with_relations.assert_called_once_with(tender_uuid)

        # 1. Check attributes of the *mock* tender were updated
        assert mock_existing_tender.title == "Updated Tender Title"
        assert mock_existing_tender.value_amount == 1200.0
        assert mock_existing_tender.status == "active.qualification"
        assert mock_existing_tender.date_modified == date_modified_api

        # 2. Check attributes of the *mock* existing bid were updated
        assert mock_existing_bid.value_amount == 980.0 # Value changed
        assert mock_existing_bid.status == "active" # Status didn't change

        # 3. Check session.add calls for *changes* and the *new* bid
        record_change_calls = [args[0] for args, kwargs in self.mock_repo.record_change.call_args_list]
        added_entities = [args[0] for args, kwargs in self.mock_repo.add_entity.call_args_list]

        # Check Tender Changes
        tender_changes_added = [obj for obj in record_change_calls if isinstance(obj, TenderChange)]
        assert len(tender_changes_added) == 3 # title, value_amount, status
        # Example check for one change
        title_change = next(tc for tc in tender_changes_added if tc.field_name == 'title')
        assert title_change.old_value == "Old Tender Title"
        assert title_change.new_value == "Updated Tender Title"
        assert title_change.tender_id == tender_uuid
        assert title_change.change_date == date_modified_api

        # Check Bid Changes (only value_amount should have changed for existing bid)
        bid_changes_added = [obj for obj in record_change_calls if isinstance(obj, BidChange)]
        assert len(bid_changes_added) == 1
        value_change = bid_changes_added[0]
        assert value_change.field_name == 'value_amount'
        assert value_change.old_value == "950.0" # Check string representation
        assert value_change.new_value == "980.0"
        assert value_change.bid_id == "bid-uuid-existing-1"
        assert value_change.change_date == date_modified_api

        # Check New Bid addition
        new_bids_added = [obj for obj in added_entities if isinstance(obj, Bid) and obj.id == "bid-uuid-new-2"]
        assert len(new_bids_added) == 1
        assert new_bids_added[0].tenderer_legal_name == "Bidder Two"
        assert new_bids_added[0].tender_id == tender_uuid

    def test_process_tender_data_deleted_bid(self, sample_legacy_details_deleted_bid):
        """Verify processing a tender where a bid is now marked as deleted."""
        tender_uuid = sample_legacy_details_deleted_bid['id']
        tender_ocid = "ocid-existing"
        date_modified_api = datetime(2025, 1, 11, 10, 0, 0, tzinfo=timezone.utc)
        gc_id = 1

         # --- Arrange ---
        # Mock existing Bid (status is active)
        mock_existing_bid = MockBid(
            id="bid-uuid-existing-1",
            tender_id=tender_uuid,
            status="active", # Old status
            value_amount=980.0
        )
        mock_existing_tender = MockTender(
            id=tender_uuid,
            ocid=tender_ocid,
            date_modified=datetime(2025, 1, 10, 15, 0, 0, tzinfo=timezone.utc), # Older date
            title="Updated Tender Title", # Assume no change from previous step
            value_amount=1200.0,
            status="active.qualification",
            general_classifier_id=gc_id,
            bids=[mock_existing_bid]
        )
        self.mock_repo.get_tender_with_relations.return_value = mock_existing_tender

        # --- Act ---
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid,
            tender_ocid=tender_ocid,
            date_modified_utc=date_modified_api,
            general_classifier_id=gc_id,
            legacy_details=sample_legacy_details_deleted_bid
        )

        # --- Assert ---
        assert result is True
        self.mock_repo.get_tender_with_relations.assert_called_once_with(tender_uuid)

        # 1. Check the mock bid's status was updated
        assert mock_existing_bid.status == "deleted"

        # 2. Check that ONLY a status change was recorded for the bid
        record_changes = [args[0] for args, kwargs in self.mock_repo.record_change.call_args_list]
        bid_changes_added = [obj for obj in record_changes if isinstance(obj, BidChange)]
        assert len(bid_changes_added) == 1
        status_change = bid_changes_added[0]
        assert status_change.field_name == 'status'
        assert status_change.old_value == "active"
        assert status_change.new_value == "deleted"
        assert status_change.bid_id == "bid-uuid-existing-1"
        assert status_change.change_date == date_modified_api

        # 3. Ensure no other BidChange records were added
        assert len(bid_changes_added) == 1

        # 4. Check Tender's date_modified was updated
        assert mock_existing_tender.date_modified == date_modified_api
        # Check if a TenderChange was added for date_modified *if* you decide to track it explicitly
        # (current code doesn't add change record for date_modified if only processing newer data)

    def test_process_tender_data_schema_load_failure(self):
        """Test failure when legacy_details cannot be loaded by the schema."""
        tender_uuid = "tender-uuid-bad"
        tender_ocid = "ocid-bad"
        date_modified = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        gc_id = 1
        bad_legacy_details = {"id": tender_uuid, "dateModified": "invalid-date"} # Invalid data

         # --- Act ---
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid,
            tender_ocid=tender_ocid,
            date_modified_utc=date_modified, # Not really used if schema fails
            general_classifier_id=gc_id,
            legacy_details=bad_legacy_details
        )

        # --- Assert ---
        assert result is False
        # Ensure no DB interactions occurred
        self.mock_repo.get_tender_with_relations.assert_not_called()
        self.mock_repo.add_entity.assert_not_called()
        self.mock_repo.flush.assert_not_called()

    def test_process_tender_data_id_mismatch(self, sample_legacy_details_new):
        """Test failure when legacy_details ID doesn't match expected UUID."""
        tender_uuid = "different-uuid" # Different from ID in fixture
        tender_ocid = "ocid-new"
        date_modified = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        gc_id = 1

        # --- Act ---
        result = self.processor.process_tender_data(
            tender_uuid=tender_uuid,
            tender_ocid=tender_ocid,
            date_modified_utc=date_modified,
            general_classifier_id=gc_id,
            legacy_details=sample_legacy_details_new # Contains "tender-uuid-new"
        )

        # --- Assert ---
        assert result is False
        # Ensure no DB interactions occurred
        self.mock_repo.get_tender_with_relations.assert_not_called()
        self.mock_repo.add_entity.assert_not_called()
        self.mock_repo.flush.assert_not_called()

