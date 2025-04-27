from datetime import datetime
from typing import Dict, Type

from sqlalchemy.orm import Session

from models import TenderChange, BidChange, AwardChange, ComplaintChange, \
    TenderDocumentChange
from repositories.change_repository import ChangeRepository
from repositories.tender_repository import TenderRepository


class ReportGenerationService:
    def __init__(self, session: Session):
        self.session = session
        self.change_repo = ChangeRepository(session)
        self.tender_repo = TenderRepository(session)

    def generate_tender_report(self, tender_id: str, since_date: datetime) -> Dict:
        """
        Generates a report for a specific tender, including new entities and changes since a given date.
        """

        tender = self.tender_repo.get_tender_with_relations(tender_id)

        if not tender:
            raise ValueError(f"Tender with ID {tender_id} not found.")

        tender_changes = self.change_repo.get_changes_since(Type[TenderChange], tender_id, since_date)


        bid_changes = self.change_repo.get_changes_since(BidChange, tender_id, since_date)
        award_changes = self.change_repo.get_changes_since(AwardChange, tender_id, since_date)
        document_changes = self.change_repo.get_changes_since(TenderDocumentChange, tender_id, since_date)
        complaint_changes = self.change_repo.get_changes_since(ComplaintChange, tender_id, since_date)

        report_data = {
            "tender": tender,
            "tender_changes": tender_changes,
            "bids": tender.bids,
            "bid_changes": bid_changes,
            "awards": tender.awards,
            "award_changes": award_changes,
            "documents": tender.documents,
            "document_changes": document_changes,
            "complaints": tender.complaints,
            "complaint_changes": complaint_changes,
        }

        return report_data

    def generate_plain_text_report(self, report_data: Dict) -> str:
        """
        Generates a plain text report from the given report data.

        Args:
            report_data: A dictionary containing the report data.

        Returns:
            A string containing the plain text report.
        """
        return ""