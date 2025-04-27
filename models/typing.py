from typing import TypeVar, Union

from sqlalchemy.ext.declarative import DeclarativeMeta

from models import (Tender, TenderDocument, Award, Bid, Complaint,
                    TenderChange, TenderDocumentChange, AwardChange, BidChange, ComplaintChange)

# Type variable for SQLAlchemy models
ModelT = TypeVar('ModelT', bound=DeclarativeMeta)

EntityT = TypeVar('EntityT', bound=Union[Tender, TenderDocument, Award, Bid, Complaint])
ChildEntityT = TypeVar('ChildEntityT', bound=Union[TenderDocument, Award, Bid, Complaint])

ChangeT = TypeVar('ChangeT', bound=Union[TenderChange, TenderDocumentChange, AwardChange, BidChange, ComplaintChange])