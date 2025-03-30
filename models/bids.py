from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Integer

from db import db


class Bid(db.Model):
    __tablename__ = 'bids'

    id = Column(String(32), primary_key=True)
    tender_id = Column(String(32), ForeignKey('tenders.id'), nullable=False)
    date = Column(DateTime)
    status = Column(String(50))
    value_amount = Column(Numeric(18, 2))

    # tenderer data
    tenderer_id = Column(String)
    tenderer_legal_name = Column(String)

    # Relationships
    tender = db.relationship("Tender", back_populates="bids")


class BidChange(db.Model):
    __tablename__ = 'bid_changes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    bid_id = Column(String(32), ForeignKey('bids.id'), nullable=False)
    change_date = Column(DateTime(timezone=True), nullable=False)
    field_name = Column(String(50), nullable=False)
    old_value = Column(String)
    new_value = Column(String)

    # Relationships
    bid = db.relationship("Bid", back_populates="changes")