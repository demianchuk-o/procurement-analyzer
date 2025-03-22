from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text, Integer

from db import db


class Bid(db.Model):
    __tablename__ = 'bids'

    id = Column(String(32), primary_key=True)
    tender_id = Column(String(32), ForeignKey('tenders.id'), nullable=False)
    date = Column(DateTime)
    status = Column(String(50))
    value_amount = Column(Numeric(18, 2))
    value_currency = Column(String(10))


    # Relationships
    tender = db.relationship("Tender", back_populates="bids")


class BidChange(db.Model):
    __tablename__ = 'bid_changes'

    id = Column(Integer, primary_key=True)
    bid_id = Column(String(32), ForeignKey('bids.id'), nullable=False) #FK на Bid
    tender_id = Column(String(32), ForeignKey('tenders.id'), nullable=False) #FK на Tender
    change_date = Column(DateTime(timezone=True), nullable=False)
    field_name = Column(String(50), nullable=False)
    old_value = Column(String)
    new_value = Column(String)


    # Relationships
    bid = db.relationship("Bid", back_populates="changes")