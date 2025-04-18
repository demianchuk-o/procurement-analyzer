from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Integer
from sqlalchemy.orm import relationship

from db import db


class Award(db.Model):
    __tablename__ = 'awards'

    id = Column(String(32), primary_key=True)
    tender_id = Column(String(32), ForeignKey('tenders.id'), nullable=False)
    bid_id = Column(String(32), ForeignKey('bids.id'), nullable = False)
    status = Column(String)
    title = Column(String)
    value_amount = Column(Numeric(18, 2))
    award_date = Column(DateTime(timezone=True))

    # periods
    complaint_period_start_date = Column(DateTime(timezone=True))
    complaint_period_end_date = Column(DateTime(timezone=True))

    # Relationships
    bid = relationship("Bid")
    tender = relationship("Tender", back_populates="awards")
    changes = relationship("AwardChange", back_populates="award",
                           order_by="AwardChange.change_date",
                           cascade="all, delete-orphan")


class AwardChange(db.Model):
    __tablename__ = 'award_changes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    award_id = Column(String(32), ForeignKey('awards.id'), nullable=False)
    change_date = Column(DateTime(timezone=True), nullable=False)
    field_name = Column(String(50), nullable=False)
    old_value = Column(String)
    new_value = Column(String)

    # Relationships
    award = db.relationship("Award", back_populates="changes")