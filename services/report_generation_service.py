import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.orm import Session

from models import TenderChange, BidChange, AwardChange, ComplaintChange, \
    TenderDocumentChange, Tender, Bid, Award, TenderDocument, Complaint
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

    def generate_tender_report(self, tender_id: str,
                               new_since: Optional[datetime] = None,
                               changes_since: Optional[datetime] = None,
                               fetch_new_entities: bool = True,
                               fetch_entity_changes: bool = True) -> Dict:
        """
        Generates a structured report dictionary for a specific tender.
        - 'new_since': Filters for entities created after this date (if fetch_new_entities is True).
        - 'changes_since': Filters for changes recorded after this date (if fetch_entity_changes is True).
        - 'fetch_new_entities': Whether to include newly created entities.
        - 'fetch_entity_changes': Whether to include historical changes to entities and the tender itself.
        """
        logger.info(
            f"Generating report for tender {tender_id} (new_since={new_since}, changes_since={changes_since}, "
            f"fetch_new={fetch_new_entities}, fetch_changes={fetch_entity_changes})"
        )

        new_since_utc = ensure_utc_aware(new_since)
        tender = self.tender_repo.get_tender_with_relations(tender_id)

        if not tender:
            logger.warning(f"Tender with ID {tender_id} not found.")
            raise ValueError(f"Tender with ID {tender_id} not found.")

        tender_info_str = get_entity_short_info(tender)

        report_data = {
            "tender_info": tender_info_str,
            "new_entities": defaultdict(list),
            "tender_changes": [],
            "entity_changes": defaultdict(lambda: defaultdict(lambda: {"info": "", "changes": []})),
        }

        if fetch_entity_changes:
            actual_changes_since = ensure_utc_aware(
                changes_since if changes_since else datetime.min.replace(tzinfo=timezone.utc))
            report_data["tender_changes"] = self.change_repo.get_changes_since(
                TenderChange, tender_id, actual_changes_since
            )

            change_map_config = [
                (BidChange, "bid_id", tender.bids, "bids", Bid),
                (AwardChange, "award_id", tender.awards, "awards", Award),
                (TenderDocumentChange, "document_id", tender.documents, "documents", TenderDocument),
                (ComplaintChange, "complaint_id", tender.complaints, "complaints", Complaint),
            ]

            for ChangeModel, entity_id_field, entity_list, report_key, EntityClassModel in change_map_config:
                changes = self.change_repo.get_changes_since(ChangeModel, tender_id, actual_changes_since)
                entity_map = {getattr(e, 'id'): e for e in entity_list}
                current_entity_changes = defaultdict(lambda: {"info": "", "changes": []})

                for change in changes:
                    entity_id = getattr(change, entity_id_field)
                    if entity_id in entity_map:
                        entity_obj = entity_map[entity_id]
                        if not current_entity_changes[entity_id]["info"]:
                            current_entity_changes[entity_id]["info"] = get_entity_short_info(entity_obj)
                        current_entity_changes[entity_id]["changes"].append(change)
                if current_entity_changes:
                    report_data["entity_changes"][report_key] = current_entity_changes

        if fetch_new_entities:
            if not new_since:
                logger.warning(
                    "fetch_new_entities is True, but new_since is not provided. No new entities will be reported.")
            else:
                new_since_utc = ensure_utc_aware(new_since)

                new_entity_configs = [
                    (tender.bids, 'date', "bids"),
                    (tender.awards, 'award_date', "awards"),
                    (tender.documents, 'date_published', "documents"),
                    (tender.complaints, 'date_submitted', "complaints"),
                ]

                for entity_list, date_attr, report_key in new_entity_configs:
                    new_items = [
                        item for item in entity_list if
                        hasattr(item, date_attr) and getattr(item, date_attr) and
                        ensure_utc_aware(getattr(item, date_attr)) > new_since_utc
                    ]
                    report_data["new_entities"][report_key] = [get_entity_short_info(item) for item in new_items]

        logger.info(f"Report generated successfully for tender {tender_id}")
        return report_data