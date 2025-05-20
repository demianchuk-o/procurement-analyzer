import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict

from sqlalchemy.orm import Session

from models import TenderChange, BidChange, AwardChange, ComplaintChange, \
    TenderDocumentChange
from repositories.change_repository import ChangeRepository
from repositories.tender_repository import TenderRepository
from util.report_helpers import get_entity_short_info
from util.datetime_utils import ensure_utc_aware

logger = logging.getLogger(__name__)


class ReportGenerationService:
    def __init__(self, session: Session):
        self.session = session
        self.change_repo = ChangeRepository(session)
        self.tender_repo = TenderRepository(session)

    def generate_tender_report(self, tender_id: str, new_since: datetime,
                               changes_since: datetime = datetime.min) -> Dict:
        """
        Generates a structured report dictionary for a specific tender, focusing on
        new entities and changes since a given date.
        """
        logger.info(f"Generating report for tender {tender_id} since {new_since}")

        new_since_utc = ensure_utc_aware(new_since)
        tender = self.tender_repo.get_tender_with_relations(tender_id)

        tender_info = get_entity_short_info(tender)

        if not tender:
            logger.warning(f"Tender with ID {tender_id} not found.")
            raise ValueError(f"Tender with ID {tender_id} not found.")

        tender_changes = self.change_repo.get_changes_since(TenderChange, tender_id, changes_since)
        bid_changes = self.change_repo.get_changes_since(BidChange, tender_id, changes_since)
        award_changes = self.change_repo.get_changes_since(AwardChange, tender_id, changes_since)
        document_changes = self.change_repo.get_changes_since(TenderDocumentChange, tender_id, changes_since)
        complaint_changes = self.change_repo.get_changes_since(ComplaintChange, tender_id, changes_since)

        new_bids = [
            b for b in tender.bids if
            hasattr(b, 'date') and b.date and
            ensure_utc_aware(b.date) > new_since_utc
        ]
        new_awards = [
            a for a in tender.awards if
            hasattr(a, 'award_date') and a.award_date and
            ensure_utc_aware(a.award_date) > new_since_utc
        ]
        new_documents = [
            d for d in tender.documents if
            hasattr(d, 'date_published') and d.date_published and
            ensure_utc_aware(d.date_published) > new_since_utc
        ]
        new_complaints = [
            c for c in tender.complaints if
            hasattr(c, 'date_submitted') and c.date_submitted and
            ensure_utc_aware(c.date_submitted) > new_since_utc
        ]


        bid_map = {b.id: b for b in tender.bids}
        award_map = {a.id: a for a in tender.awards}
        doc_map = {d.id: d for d in tender.documents}
        complaint_map = {c.id: c for c in tender.complaints}

        # Group changes by entity type
        bid_entity_changes = defaultdict(lambda: {"info": "", "changes": []})
        award_entity_changes = defaultdict(lambda: {"info": "", "changes": []})
        doc_entity_changes = defaultdict(lambda: {"info": "", "changes": []})
        complaint_entity_changes = defaultdict(lambda: {"info": "", "changes": []})

        for change in bid_changes:
            if change.bid_id in bid_map:
                bid_obj = bid_map[change.bid_id]
                if not bid_entity_changes[change.bid_id]["info"]:
                     bid_entity_changes[change.bid_id]["info"] = get_entity_short_info(bid_obj)
                bid_entity_changes[change.bid_id]["changes"].append(change)

        for change in award_changes:
            if change.award_id in award_map:
                award_obj = award_map[change.award_id]
                if not award_entity_changes[change.award_id]["info"]:
                    award_entity_changes[change.award_id]["info"] = get_entity_short_info(award_obj)
                award_entity_changes[change.award_id]["changes"].append(change)

        for change in document_changes:
             if change.document_id in doc_map:
                 doc_obj = doc_map[change.document_id]
                 if not doc_entity_changes[change.document_id]["info"]:
                     doc_entity_changes[change.document_id]["info"] = get_entity_short_info(doc_obj)
                 doc_entity_changes[change.document_id]["changes"].append(change)

        for change in complaint_changes:
            complaint_obj = complaint_map.get(change.complaint_id)
            if change.complaint_id in complaint_map:
                if not complaint_entity_changes[change.complaint_id]["info"]:
                    complaint_entity_changes[change.complaint_id]["info"] = get_entity_short_info(complaint_obj)
                complaint_entity_changes[change.complaint_id]["changes"].append(change)



        # Structure the report data
        report_data = {
            "tender_info": tender_info,
            "tender_changes": tender_changes,
            "new_entities": {
                "bids": new_bids,
                "awards": new_awards,
                "documents": new_documents,
                "complaints": new_complaints,
            },
            "entity_changes": {
                "bids": bid_entity_changes,
                "awards": award_entity_changes,
                "documents": doc_entity_changes,
                "complaints": complaint_entity_changes,
            }
        }

        logger.info(f"Report generated successfully for tender {tender_id}")
        return report_data