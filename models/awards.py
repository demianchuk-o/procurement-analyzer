from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text, Integer
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
    award_date = Column(DateTime)

    # Relationships
    tender = relationship("Tender", back_populates="awards")
    bid = relationship("Bid", back_populates="award")


class AwardChange(db.Model):
    __tablename__ = 'award_changes'

    id = Column(Integer, primary_key=True)
    award_id = Column(String(32), ForeignKey('awards.id'), nullable=False)
    tender_id = Column(String(32), ForeignKey('tenders.id'), nullable=False)
    bid_id = Column(String(32), ForeignKey('bids.id'), nullable=False)
    change_date = Column(DateTime(timezone=True), nullable=False)
    field_name = Column(String(50), nullable=False)
    old_value = Column(String)
    new_value = Column(String)

    # Relationships
    award = db.relationship("Award", back_populates="changes")