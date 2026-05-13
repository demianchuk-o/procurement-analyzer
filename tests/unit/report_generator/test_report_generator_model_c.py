import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from services.report_generation_service import ReportGenerationService

@pytest.fixture
def mock_session():
    return MagicMock()

@pytest.fixture
def mock_dependencies():
    with patch('services.report_generation_service.ChangeRepository') as MockChangeRepo, \
         patch('services.report_generation_service.TenderRepository') as MockTenderRepo, \
         patch('services.report_generation_service.get_entity_short_info') as mock_get_info, \
         patch('services.report_generation_service.ensure_utc_aware') as mock_ensure_utc:
        
        mock_get_info.return_value = "Short Info"
        mock_ensure_utc.side_effect = lambda x: x if x else datetime.min.replace(tzinfo=timezone.utc)
        
        yield {
            "ChangeRepository": MockChangeRepo,
            "TenderRepository": MockTenderRepo,
            "get_entity_short_info": mock_get_info,
            "ensure_utc_aware": mock_ensure_utc,
        }

@pytest.fixture
def service(mock_session, mock_dependencies):
    return ReportGenerationService(mock_session)

def test_generate_tender_report_not_found(service):
    service.tender_repo.get_tender_with_relations.return_value = None
    
    with pytest.raises(ValueError, match=r"Tender with ID test_tender not found\."):
        service.generate_tender_report("test_tender")

def test_generate_tender_report_fetch_new_no_since(service):
    tender_mock = MagicMock()
    tender_mock.id = "test_tender"
    service.tender_repo.get_tender_with_relations.return_value = tender_mock
    
    with patch('services.report_generation_service.logger.warning') as mock_logger:
        result = service.generate_tender_report(
            "test_tender", 
            new_since=None, 
            fetch_new_entities=True, 
            fetch_entity_changes=False
        )
        
        mock_logger.assert_called_with("fetch_new_entities is True, but new_since is not provided. No new entities will be reported.")
        assert "bids" not in result["new_entities"]

def test_generate_tender_report_full_coverage(service, mock_dependencies):
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new_since_time = base_time + timedelta(days=1)
    
    # Mocking Tender and related entities
    tender_mock = MagicMock()
    tender_mock.id = "test_tender"
    
    # Bid 1: Old (should be excluded from new_entities), Bid 2: New (should be included)
    bid_old = MagicMock()
    bid_old.id = "bid_1"
    bid_old.date = base_time
    
    bid_new = MagicMock()
    bid_new.id = "bid_2"
    bid_new.date = base_time + timedelta(days=2)
    
    tender_mock.bids = [bid_old, bid_new]
    
    # Complaint 1: New (should be included)
    complaint_new = MagicMock()
    complaint_new.id = "comp_1"
    complaint_new.date_submitted = base_time + timedelta(days=2)
    tender_mock.complaints = [complaint_new]
    
    tender_mock.awards = []
    tender_mock.documents = []
    
    service.tender_repo.get_tender_with_relations.return_value = tender_mock
    
    # Mocking changes
    tender_change = MagicMock()
    tender_change.id = "t_change_1"
    
    bid_change = MagicMock()
    bid_change.id = "b_change_1"
    bid_change.bid_id = "bid_1"
    
    complaint_change = MagicMock()
    complaint_change.id = "c_change_1"
    complaint_change.complaint_id = "comp_1"
    
    def side_effect_get_changes_since(change_model, tender_id, changes_since):
        if change_model.__name__ == 'TenderChange':
            return [tender_change]
        elif change_model.__name__ == 'BidChange':
            return [bid_change]
        elif change_model.__name__ == 'ComplaintChange':
            return [complaint_change]
        return []

    service.change_repo.get_changes_since.side_effect = side_effect_get_changes_since
    
    # To properly test datetime comparisons, update ensure_utc_aware mock for this specific test
    mock_dependencies["ensure_utc_aware"].side_effect = lambda x: x if getattr(x, 'tzinfo', None) else x.replace(tzinfo=timezone.utc)
    
    result = service.generate_tender_report(
        "test_tender",
        new_since=new_since_time,
        changes_since=base_time,
        fetch_new_entities=True,
        fetch_entity_changes=True
    )
    
    assert result["tender_info"] == "Short Info"
    assert result["tender_changes"] == [tender_change]
    
    # Asserting new_entities filtering (Bid 2 and Complaint 1 should be included, Bid 1 excluded)
    assert len(result["new_entities"]["bids"]) == 1
    assert result["new_entities"]["bids"][0] == "Short Info"
    
    assert len(result["new_entities"]["complaints"]) == 1
    assert result["new_entities"]["complaints"][0] == "Short Info"
    
    # Asserting entity_changes mapping
    assert "bid_1" in result["entity_changes"]["bids"]
    assert result["entity_changes"]["bids"]["bid_1"]["info"] == "Short Info"
    assert result["entity_changes"]["bids"]["bid_1"]["changes"] == [bid_change]
    
    assert "comp_1" in result["entity_changes"]["complaints"]
    assert result["entity_changes"]["complaints"]["comp_1"]["info"] == "Short Info"
    assert result["entity_changes"]["complaints"]["comp_1"]["changes"] == [complaint_change]