from typing import Dict, Type

from models import AwardChange, BidChange, TenderChange, TenderDocumentChange, ComplaintChange
from models.typing import ChangeT
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Numeric

CHANGE_FK_NAMES: Dict[Type, Column] = {
    AwardChange: AwardChange.award_id,
    BidChange: BidChange.bid_id,
    TenderChange: TenderChange.tender_id,
    TenderDocumentChange: TenderDocumentChange.document_id,
    ComplaintChange: ComplaintChange.complaint_id,
}