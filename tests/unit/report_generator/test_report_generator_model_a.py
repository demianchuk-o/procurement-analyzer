import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest
from sqlalchemy.orm import Session

import services.report_generation_service as report_module
from services.report_generation_service import (
    AwardChange,
    BidChange,
    ComplaintChange,
    ReportGenerationService,
    TenderChange,
    TenderDocumentChange,
)


def make_entity(entity_id, **attrs):
    return SimpleNamespace(id=entity_id, **attrs)


def make_change(**attrs):
    return SimpleNamespace(**attrs)


@pytest.fixture
def report_service_context():
    session = MagicMock(spec=Session)
    change_repo = MagicMock()
    tender_repo = MagicMock()

    with patch.object(report_module, "ChangeRepository", return_value=change_repo), \
         patch.object(report_module, "TenderRepository", return_value=tender_repo), \
         patch.object(report_module, "get_entity_short_info", side_effect=lambda obj: f"INFO:{obj.id}"), \
         patch.object(report_module, "ensure_utc_aware", side_effect=lambda value: value):
        service = ReportGenerationService(session)
        yield service, change_repo, tender_repo


def test_generate_tender_report_raises_when_tender_not_found(report_service_context):
    service, change_repo, tender_repo = report_service_context

    tender_repo.get_tender_with_relations.return_value = None

    with pytest.raises(ValueError, match="Tender with ID tender-404 not found."):
        service.generate_tender_report("tender-404")

    tender_repo.get_tender_with_relations.assert_called_once_with("tender-404")
    change_repo.get_changes_since.assert_not_called()


def test_generate_tender_report_warns_when_new_since_missing(report_service_context, caplog):
    service, change_repo, tender_repo = report_service_context

    tender_repo.get_tender_with_relations.return_value = make_entity(
        "tender-1",
        bids=[],
        awards=[],
        documents=[],
        complaints=[],
    )

    caplog.set_level(logging.WARNING)

    result = service.generate_tender_report(
        "tender-1",
        fetch_new_entities=True,
        fetch_entity_changes=False,
    )

    assert result["tender_info"] == "INFO:tender-1"
    assert result["tender_changes"] == []
    assert dict(result["new_entities"]) == {}
    assert dict(result["entity_changes"]) == {}
    assert "fetch_new_entities is True, but new_since is not provided" in caplog.text

    tender_repo.get_tender_with_relations.assert_called_once_with("tender-1")
    change_repo.get_changes_since.assert_not_called()


def test_generate_tender_report_returns_empty_optional_sections_when_disabled(report_service_context):
    service, change_repo, tender_repo = report_service_context

    tender_repo.get_tender_with_relations.return_value = make_entity(
        "tender-2",
        bids=[make_entity("bid-1", date=datetime(2024, 1, 1, tzinfo=timezone.utc))],
        awards=[make_entity("award-1", award_date=datetime(2024, 1, 1, tzinfo=timezone.utc))],
        documents=[make_entity("doc-1", date_published=datetime(2024, 1, 1, tzinfo=timezone.utc))],
        complaints=[make_entity("complaint-1", date_submitted=datetime(2024, 1, 1, tzinfo=timezone.utc))],
    )

    result = service.generate_tender_report(
        "tender-2",
        fetch_new_entities=False,
        fetch_entity_changes=False,
    )

    assert result["tender_info"] == "INFO:tender-2"
    assert result["tender_changes"] == []
    assert dict(result["new_entities"]) == {}
    assert dict(result["entity_changes"]) == {}

    tender_repo.get_tender_with_relations.assert_called_once_with("tender-2")
    change_repo.get_changes_since.assert_not_called()


def test_generate_tender_report_filters_new_entities_and_entity_changes(report_service_context):
    service, change_repo, tender_repo = report_service_context

    older = datetime(2024, 1, 1, tzinfo=timezone.utc)
    newer = datetime(2024, 1, 10, tzinfo=timezone.utc)
    new_since = datetime(2024, 1, 5, tzinfo=timezone.utc)
    changes_since = datetime(2024, 1, 7, tzinfo=timezone.utc)

    tender = make_entity(
        "tender-3",
        bids=[
            make_entity("bid-old", date=older),
            make_entity("bid-new", date=newer),
        ],
        awards=[
            make_entity("award-old", award_date=older),
            make_entity("award-new", award_date=newer),
        ],
        documents=[
            make_entity("doc-old", date_published=older),
            make_entity("doc-new", date_published=newer),
        ],
        complaints=[
            make_entity("complaint-old", date_submitted=older),
            make_entity("complaint-new", date_submitted=newer),
        ],
    )
    tender_repo.get_tender_with_relations.return_value = tender

    tender_changes = [make_change(field_name="title", old_value="Old", new_value="New")]
    bid_change_known = make_change(bid_id="bid-new", field_name="value_amount", old_value="100", new_value="200")
    bid_change_ignored = make_change(bid_id="bid-missing", field_name="value_amount", old_value="1", new_value="2")
    award_change = make_change(award_id="award-new", field_name="status", old_value="draft", new_value="awarded")
    document_change = make_change(
        document_id="doc-new",
        field_name="title",
        old_value="Old doc",
        new_value="New doc",
    )
    complaint_change_known = make_change(
        complaint_id="complaint-new",
        field_name="status",
        old_value="open",
        new_value="closed",
    )
    complaint_change_ignored = make_change(
        complaint_id="complaint-missing",
        field_name="status",
        old_value="open",
        new_value="rejected",
    )

    change_map = {
        TenderChange: tender_changes,
        BidChange: [bid_change_known, bid_change_ignored],
        AwardChange: [award_change],
        TenderDocumentChange: [document_change],
        ComplaintChange: [complaint_change_known, complaint_change_ignored],
    }
    change_repo.get_changes_since.side_effect = lambda model, tender_id, since: change_map[model]

    result = service.generate_tender_report(
        "tender-3",
        new_since=new_since,
        changes_since=changes_since,
        fetch_new_entities=True,
        fetch_entity_changes=True,
    )

    assert result["tender_info"] == "INFO:tender-3"
    assert result["tender_changes"] is tender_changes

    assert change_repo.get_changes_since.call_args_list == [
        call(TenderChange, "tender-3", changes_since),
        call(BidChange, "tender-3", changes_since),
        call(AwardChange, "tender-3", changes_since),
        call(TenderDocumentChange, "tender-3", changes_since),
        call(ComplaintChange, "tender-3", changes_since),
    ]

    assert result["new_entities"]["bids"] == ["INFO:bid-new"]
    assert result["new_entities"]["awards"] == ["INFO:award-new"]
    assert result["new_entities"]["documents"] == ["INFO:doc-new"]
    assert result["new_entities"]["complaints"] == ["INFO:complaint-new"]

    assert result["entity_changes"]["bids"]["bid-new"]["info"] == "INFO:bid-new"
    assert result["entity_changes"]["bids"]["bid-new"]["changes"] == [bid_change_known]
    assert "bid-missing" not in result["entity_changes"]["bids"]

    assert result["entity_changes"]["complaints"]["complaint-new"]["info"] == "INFO:complaint-new"
    assert result["entity_changes"]["complaints"]["complaint-new"]["changes"] == [complaint_change_known]
    assert "complaint-missing" not in result["entity_changes"]["complaints"]

    assert result["entity_changes"]["awards"]["award-new"]["changes"] == [award_change]
    assert result["entity_changes"]["documents"]["doc-new"]["changes"] == [document_change]

    tender_repo.get_tender_with_relations.assert_called_once_with("tender-3")


def test_generate_tender_report_uses_min_datetime_when_changes_since_missing(report_service_context):
    service, change_repo, tender_repo = report_service_context

    tender_repo.get_tender_with_relations.return_value = make_entity(
        "tender-4",
        bids=[],
        awards=[],
        documents=[],
        complaints=[],
    )

    change_repo.get_changes_since.side_effect = lambda model, tender_id, since: []

    result = service.generate_tender_report(
        "tender-4",
        new_since=None,
        changes_since=None,
        fetch_new_entities=False,
        fetch_entity_changes=True,
    )

    min_aware = datetime.min.replace(tzinfo=timezone.utc)

    assert result["tender_info"] == "INFO:tender-4"
    assert result["tender_changes"] == []
    assert dict(result["new_entities"]) == {}
    assert dict(result["entity_changes"]) == {}

    assert change_repo.get_changes_since.call_args_list == [
        call(TenderChange, "tender-4", min_aware),
        call(BidChange, "tender-4", min_aware),
        call(AwardChange, "tender-4", min_aware),
        call(TenderDocumentChange, "tender-4", min_aware),
        call(ComplaintChange, "tender-4", min_aware),
    ]

    tender_repo.get_tender_with_relations.assert_called_once_with("tender-4")