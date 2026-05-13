import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from collections import defaultdict

from services.report_generation_service import ReportGenerationService
from models import (
    TenderChange, BidChange, AwardChange, ComplaintChange,
    TenderDocumentChange, Tender, Bid, Award, TenderDocument, Complaint
)


@pytest.fixture
def mock_session():
    return Mock()


@pytest.fixture
def mock_change_repo():
    return Mock()


@pytest.fixture
def mock_tender_repo():
    return Mock()


@pytest.fixture
def report_service(mock_session, mock_change_repo, mock_tender_repo):
    service = ReportGenerationService(mock_session)
    service.change_repo = mock_change_repo
    service.tender_repo = mock_tender_repo
    return service


@pytest.fixture
def utc_now():
    return datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def utc_past():
    return datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def utc_future():
    return datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_tender_not_found(mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo):
    mock_tender_repo.get_tender_with_relations.return_value = None
    
    with pytest.raises(ValueError, match="Tender with ID test_tender_id not found"):
        report_service.generate_tender_report("test_tender_id")


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_generate_full_report_with_bids_and_complaints(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, utc_past, utc_future
):
    date_map = {id(utc_past): utc_past, id(utc_now): utc_now, id(utc_future): utc_future}
    
    def ensure_utc_side_effect(dt):
        if dt is None:
            return None
        if dt == utc_past or dt == utc_now or dt == utc_future:
            return dt
        return dt
    
    mock_ensure_utc.side_effect = ensure_utc_side_effect
    mock_get_short_info.side_effect = lambda obj: f"{obj.__class__.__name__}(id={getattr(obj, 'id', 'unknown')})"

    bid1 = Mock(spec=Bid)
    bid1.id = "bid_1"
    bid1.date = utc_now
    
    bid2 = Mock(spec=Bid)
    bid2.id = "bid_2"
    bid2.date = utc_past
    
    complaint1 = Mock(spec=Complaint)
    complaint1.id = "complaint_1"
    complaint1.date_submitted = utc_now
    
    award1 = Mock(spec=Award)
    award1.id = "award_1"
    award1.award_date = utc_past
    
    doc1 = Mock(spec=TenderDocument)
    doc1.id = "doc_1"
    doc1.date_published = utc_now
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = [bid1, bid2]
    tender.complaints = [complaint1]
    tender.awards = [award1]
    tender.documents = [doc1]
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    
    tender_change1 = Mock(spec=TenderChange)
    bid_change1 = Mock(spec=BidChange)
    bid_change1.bid_id = "bid_1"
    complaint_change1 = Mock(spec=ComplaintChange)
    complaint_change1.complaint_id = "complaint_1"
    
    mock_change_repo.get_changes_since.side_effect = [
        [tender_change1],
        [bid_change1],
        [],
        [],
        [complaint_change1],
    ]
    
    report = report_service.generate_tender_report(
        "tender_123",
        new_since=utc_past,
        changes_since=utc_past,
        fetch_new_entities=True,
        fetch_entity_changes=True
    )
    
    assert report["tender_info"] == "Tender(id=tender_123)"
    assert len(report["tender_changes"]) == 1
    assert "bids" in report["new_entities"]
    assert "complaints" in report["new_entities"]
    assert "bids" in report["entity_changes"]
    assert "complaint_1" in report["entity_changes"]["complaints"]
    assert len(report["entity_changes"]["complaints"]["complaint_1"]["changes"]) == 1


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_fetch_new_entities_true_without_new_since(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, caplog
):
    mock_ensure_utc.side_effect = lambda dt: dt if dt is None else utc_now
    mock_get_short_info.return_value = "Tender()"
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = []
    tender.complaints = []
    tender.awards = []
    tender.documents = []
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    mock_change_repo.get_changes_since.return_value = []
    
    with caplog.at_level('WARNING'):
        report = report_service.generate_tender_report(
            "tender_123",
            new_since=None,
            changes_since=utc_now,
            fetch_new_entities=True,
            fetch_entity_changes=True
        )
    
    assert "fetch_new_entities is True, but new_since is not provided" in caplog.text


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_fetch_new_entities_false(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, utc_past
):
    mock_ensure_utc.side_effect = lambda dt: dt if dt is None else utc_now
    mock_get_short_info.return_value = "Tender()"
    
    bid = Mock(spec=Bid)
    bid.id = "bid_1"
    bid.date = utc_now
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = [bid]
    tender.complaints = []
    tender.awards = []
    tender.documents = []
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    mock_change_repo.get_changes_since.return_value = []
    
    report = report_service.generate_tender_report(
        "tender_123",
        new_since=utc_past,
        changes_since=utc_past,
        fetch_new_entities=False,
        fetch_entity_changes=True
    )
    
    assert report["new_entities"] == defaultdict(list)


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_fetch_entity_changes_false(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, utc_past
):
    mock_ensure_utc.side_effect = lambda dt: dt if dt is None else utc_now
    mock_get_short_info.return_value = "Tender()"
    
    bid = Mock(spec=Bid)
    bid.id = "bid_1"
    bid.date = utc_now
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = [bid]
    tender.complaints = []
    tender.awards = []
    tender.documents = []
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    
    report = report_service.generate_tender_report(
        "tender_123",
        new_since=utc_past,
        changes_since=utc_past,
        fetch_new_entities=True,
        fetch_entity_changes=False
    )
    
    assert report["tender_changes"] == []


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_both_fetch_flags_false(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, utc_past
):
    mock_ensure_utc.side_effect = lambda dt: dt if dt is None else utc_now
    mock_get_short_info.return_value = "Tender(id=123)"
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = []
    tender.complaints = []
    tender.awards = []
    tender.documents = []
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    
    report = report_service.generate_tender_report(
        "tender_123",
        new_since=utc_past,
        changes_since=utc_past,
        fetch_new_entities=False,
        fetch_entity_changes=False
    )
    
    assert report["tender_info"] == "Tender(id=123)"
    assert report["tender_changes"] == []
    assert report["new_entities"] == defaultdict(list)


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_date_filtering_new_entities(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, utc_past, utc_future
):
    def ensure_utc_side_effect(dt):
        if dt is None:
            return None
        return dt
    
    mock_ensure_utc.side_effect = ensure_utc_side_effect
    mock_get_short_info.side_effect = lambda obj: f"{obj.id}"
    
    bid_old = Mock(spec=Bid)
    bid_old.id = "bid_old"
    bid_old.date = utc_past
    
    bid_new = Mock(spec=Bid)
    bid_new.id = "bid_new"
    bid_new.date = utc_future
    
    complaint_old = Mock(spec=Complaint)
    complaint_old.id = "complaint_old"
    complaint_old.date_submitted = utc_past
    
    complaint_new = Mock(spec=Complaint)
    complaint_new.id = "complaint_new"
    complaint_new.date_submitted = utc_future
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = [bid_old, bid_new]
    tender.complaints = [complaint_old, complaint_new]
    tender.awards = []
    tender.documents = []
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    mock_change_repo.get_changes_since.return_value = []
    
    report = report_service.generate_tender_report(
        "tender_123",
        new_since=utc_now,
        fetch_new_entities=True,
        fetch_entity_changes=False
    )
    
    assert len(report["new_entities"]["bids"]) == 1
    assert report["new_entities"]["bids"][0] == "bid_new"
    assert len(report["new_entities"]["complaints"]) == 1
    assert report["new_entities"]["complaints"][0] == "complaint_new"


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_entities_without_date_attribute(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, utc_past
):
    mock_ensure_utc.side_effect = lambda dt: dt if dt is None else utc_now
    mock_get_short_info.return_value = "Tender()"
    
    bid_no_date = Mock(spec=Bid)
    bid_no_date.id = "bid_no_date"
    bid_no_date.date = None
    
    bid_with_date = Mock(spec=Bid)
    bid_with_date.id = "bid_with_date"
    bid_with_date.date = utc_now
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = [bid_no_date, bid_with_date]
    tender.complaints = []
    tender.awards = []
    tender.documents = []
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    mock_change_repo.get_changes_since.return_value = []
    
    report = report_service.generate_tender_report(
        "tender_123",
        new_since=utc_past,
        fetch_new_entities=True,
        fetch_entity_changes=False
    )
    
    assert len(report["new_entities"]["bids"]) == 1


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_multiple_changes_per_entity_complaint(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, utc_past
):
    mock_ensure_utc.side_effect = lambda dt: dt if dt is None else utc_now
    mock_get_short_info.side_effect = lambda obj: f"Complaint({obj.id})"
    
    complaint = Mock(spec=Complaint)
    complaint.id = "complaint_1"
    complaint.date_submitted = utc_now
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = []
    tender.complaints = [complaint]
    tender.awards = []
    tender.documents = []
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    
    change1 = Mock(spec=ComplaintChange)
    change1.complaint_id = "complaint_1"
    change1.field = "status"
    
    change2 = Mock(spec=ComplaintChange)
    change2.complaint_id = "complaint_1"
    change2.field = "resolution"
    
    mock_change_repo.get_changes_since.side_effect = [
        [],
        [change1, change2],
    ]
    
    report = report_service.generate_tender_report(
        "tender_123",
        new_since=utc_past,
        changes_since=utc_past,
        fetch_new_entities=True,
        fetch_entity_changes=True
    )
    
    assert "complaints" in report["entity_changes"]
    assert "complaint_1" in report["entity_changes"]["complaints"]
    assert report["entity_changes"]["complaints"]["complaint_1"]["info"] == "Complaint(complaint_1)"
    assert len(report["entity_changes"]["complaints"]["complaint_1"]["changes"]) == 2


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_change_for_missing_entity(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, utc_past
):
    mock_ensure_utc.side_effect = lambda dt: dt if dt is None else utc_now
    mock_get_short_info.return_value = "Tender()"
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = []
    tender.complaints = []
    tender.awards = []
    tender.documents = []
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    
    bid_change = Mock(spec=BidChange)
    bid_change.bid_id = "nonexistent_bid"
    
    mock_change_repo.get_changes_since.side_effect = [
        [],
        [bid_change],
        [],
        [],
        [],
    ]
    
    report = report_service.generate_tender_report(
        "tender_123",
        new_since=utc_past,
        changes_since=utc_past,
        fetch_new_entities=True,
        fetch_entity_changes=True
    )
    
    assert "bids" not in report["entity_changes"] or len(report["entity_changes"]["bids"]) == 0


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_awards_and_documents_coverage(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, utc_past
):
    mock_ensure_utc.side_effect = lambda dt: dt if dt is None else utc_now
    mock_get_short_info.side_effect = lambda obj: f"{obj.__class__.__name__}({obj.id})"
    
    award = Mock(spec=Award)
    award.id = "award_1"
    award.award_date = utc_now
    
    doc = Mock(spec=TenderDocument)
    doc.id = "doc_1"
    doc.date_published = utc_now
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = []
    tender.complaints = []
    tender.awards = [award]
    tender.documents = [doc]
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    mock_change_repo.get_changes_since.return_value = []
    
    report = report_service.generate_tender_report(
        "tender_123",
        new_since=utc_past,
        fetch_new_entities=True,
        fetch_entity_changes=False
    )
    
    assert "awards" in report["new_entities"]
    assert len(report["new_entities"]["awards"]) == 1
    assert "documents" in report["new_entities"]
    assert len(report["new_entities"]["documents"]) == 1


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_entity_changes_info_populated(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, utc_past
):
    mock_ensure_utc.side_effect = lambda dt: dt if dt is None else utc_now
    mock_get_short_info.side_effect = lambda obj: f"Bid({obj.id})"
    
    bid1 = Mock(spec=Bid)
    bid1.id = "bid_1"
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = [bid1]
    tender.complaints = []
    tender.awards = []
    tender.documents = []
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    
    bid_change = Mock(spec=BidChange)
    bid_change.bid_id = "bid_1"
    
    mock_change_repo.get_changes_since.side_effect = [
        [],
        [bid_change],
        [],
        [],
        [],
    ]
    
    report = report_service.generate_tender_report(
        "tender_123",
        new_since=utc_past,
        changes_since=utc_past,
        fetch_new_entities=True,
        fetch_entity_changes=True
    )
    
    assert "bids" in report["entity_changes"]
    assert "bid_1" in report["entity_changes"]["bids"]
    assert report["entity_changes"]["bids"]["bid_1"]["info"] == "Bid(bid_1)"
    assert len(report["entity_changes"]["bids"]["bid_1"]["changes"]) == 1


@patch('services.report_generation_service.ensure_utc_aware')
@patch('services.report_generation_service.get_entity_short_info')
def test_multiple_entities_same_type_with_changes(
    mock_get_short_info, mock_ensure_utc, report_service, mock_tender_repo,
    mock_change_repo, utc_now, utc_past
):
    mock_ensure_utc.side_effect = lambda dt: dt if dt is None else utc_now
    mock_get_short_info.side_effect = lambda obj: f"Complaint({obj.id})"
    
    complaint1 = Mock(spec=Complaint)
    complaint1.id = "complaint_1"
    complaint1.date_submitted = utc_now
    
    complaint2 = Mock(spec=Complaint)
    complaint2.id = "complaint_2"
    complaint2.date_submitted = utc_now
    
    tender = Mock(spec=Tender)
    tender.id = "tender_123"
    tender.bids = []
    tender.complaints = [complaint1, complaint2]
    tender.awards = []
    tender.documents = []
    
    mock_tender_repo.get_tender_with_relations.return_value = tender
    
    change1 = Mock(spec=ComplaintChange)
    change1.complaint_id = "complaint_1"
    
    change2 = Mock(spec=ComplaintChange)
    change2.complaint_id = "complaint_2"
    
    mock_change_repo.get_changes_since.side_effect = [
        [],
        [change1, change2],
    ]
    
    report = report_service.generate_tender_report(
        "tender_123",
        new_since=utc_past,
        changes_since=utc_past,
        fetch_new_entities=True,
        fetch_entity_changes=True
    )
    
    assert len(report["entity_changes"]["complaints"]) == 2
    assert "complaint_1" in report["entity_changes"]["complaints"]
    assert "complaint_2" in report["entity_changes"]["complaints"]