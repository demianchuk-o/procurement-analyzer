from datetime import datetime, timedelta
from typing import List, Dict, Type

from sqlalchemy.orm import Session

from models import Tender, Bid, TenderChange, BidChange, Award, AwardChange, TenderDocument, Complaint, ComplaintChange
from repositories.change_repository import ChangeRepository
from repositories.tender_repository import TenderRepository
from util.field_maps import BID_FIELD_MAP


class ReportGenerationService:
    def __init__(self, session: Session):
        self.session = session
        self.change_repo = ChangeRepository(session)
        self.tender_repo = TenderRepository(session)

    def generate_tender_report(self, tender_id: str, since_date: datetime) -> Dict:
        """
        Generates a report for a specific tender, including new entities and changes since a given date.

        Args:
            tender_id: The ID of the tender to generate the report for.
            since_date: The datetime object representing the start of the time range.

        Returns:
            A dictionary containing the report data, including tender details, new entities, and changes.
        """

        tender = self.tender_repo.get_tender_with_relations(tender_id)

        if not tender:
            raise ValueError(f"Tender with ID {tender_id} not found.")

        tender_changes = self.change_repo.get_changes_since(Type[TenderChange], tender_id, since_date)

        new_awards = self.change_repo.get_new_entries_since(Type[Award], tender_id, since_date)
        award_changes = self.change_repo.get_changes_since(Type[AwardChange], tender_id, since_date)

        new_bids = self.change_repo.get_new_entries_since(Type[Bid], tender_id, since_date)
        bid_changes = self.change_repo.get_changes_since(Type[BidChange], tender_id, since_date)

        new_documents = self.change_repo.get_new_entries_since(Type[TenderDocument], tender_id, since_date)
        document_changes = self.change_repo.get_changes_since(Type[TenderDocument], tender_id, since_date)

        new_complaints = self.change_repo.get_changes_since(Type[Complaint], tender_id, since_date)
        complaint_changes = self.change_repo.get_changes_since(Type[ComplaintChange], tender_id, since_date)

        report_data = {
            "tender": tender,
            "tender_changes": tender_changes,
            "new_bids": new_bids,
            "bid_changes": bid_changes,
            "new_awards": new_awards,
            "award_changes": award_changes,
            "new_documents": new_documents,
            "document_changes": document_changes,
            "new_complaints": new_complaints,
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
        tender = report_data["tender"]
        report = f"Тендер: {tender.title} ({tender.id})\n"
        report += f"--------------------------------------\n\n"

        if report_data["tender_changes"]:
            report += "Зміни в тендері:\n"
            for change in report_data["tender_changes"]:
                report += f"  - {change.field_name}: {change.old_value} -> {change.new_value} ({change.change_date})\n"
            report += "\n"

        if report_data["new_bids"]:
            report += "Нові пропозиції:\n"
            for bid in report_data["new_bids"]:
                report += f"ID: {bid.id}, {BID_FIELD_MAP['date']}: {bid.date}, {BID_FIELD_MAP['value_amount']}: {bid.value_amount}\n"
            report += "\n"

        if report_data["bid_changes"]:
            report += "Зміни в пропозиціях:\n"
            for change in report_data["bid_changes"]:
                report += f"ID: {change.bid_id},  {BID_FIELD_MAP[change.field_name]}, {change.old_value} -> {change.new_value}; ({change.change_date})\n"
            report += "\n"

        if report_data["new_awards"]:
            report += "New Awards:\n"
            for award in report_data["new_awards"]:
                report += f"  - Award ID: {award.id}, Date: {award.date}, Value: {award.value_amount}\n"
            report += "\n"

        if report_data["award_changes"]:
            report += "Award Changes:\n"
            for change in report_data["award_changes"]:
                report += f"  - Award ID: {change.award_id}, Field: {change.field_name}, Old Value: {change.old_value}, New Value: {change.new_value} ({change.change_date})\n"
            report += "\n"

        if report_data["new_documents"]:
            report += "New Documents:\n"
            for document in report_data["new_documents"]:
                report += f"  - Document ID: {document.id}, Date: {document.date}, Type: {document.document_type}\n"
            report += "\n"

        if report_data["document_changes"]:
            report += "Document Changes:\n"
            for change in report_data["document_changes"]:
                report += f"  - Document ID: {change.document_id}, Field: {change.field_name}, Old Value: {change.old_value}, New Value: {change.new_value} ({change.change_date})\n"
            report += "\n"

        if report_data["new_complaints"]:
            report += "New Complaints:\n"
            for complaint in report_data["new_complaints"]:
                report += f"  - Complaint ID: {complaint.id}, Date: {complaint.date}, Status: {complaint.status}\n"
            report += "\n"

        if report_data["complaint_changes"]:
            report += "Complaint Changes:\n"
            for change in report_data["complaint_changes"]:
                report += f"  - Complaint ID: {change.complaint_id}, Field: {change.field_name}, Old Value: {change.old_value}, New Value: {change.new_value} ({change.change_date})\n"
            report += "\n"

        return report