from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Numeric

from db import db


class Tender(db.Model):
    __tablename__ = 'tenders'

    id = Column(String(32), primary_key=True)
    date_created = Column(DateTime, nullable=False)
    date_modified = Column(DateTime, nullable=False)
    title = Column(Text, nullable=False)
    value_amount = Column(Numeric(18, 2))
    status = Column(String)
    enquiry_period_start_date = Column(DateTime)
    enquiry_period_end_date = Column(DateTime)
    tender_period_start_date = Column(DateTime)
    tender_period_end_date = Column(DateTime)
    auction_period_start_date = Column(DateTime)
    auction_period_end_date = Column(DateTime)
    award_period_start_date = Column(DateTime)
    award_period_end_date = Column(DateTime)
    notice_publication_date = Column(DateTime)
    item_classification_id = Column(String(32), ForeignKey('item_classifications.id'))

    # Relationships
    item_classification = db.relationship("ItemClassification", back_populates="tenders")
    awards = db.relationship("Award", back_populates="tender",
                            cascade="all, delete-orphan")
    bids = db.relationship("Bid", back_populates="tender",
                            cascade="all, delete-orphan")
    complaints = db.relationship("Complaint", back_populates="tender",
                                 cascade="all, delete-orphan")
    documents = db.relationship("TenderDocument", back_populates="tender",
                                 cascade="all, delete-orphan")
    changes = db.relationship("TenderChange", back_populates="tender",
                              order_by="TenderChange.changeDate",
                              cascade="all, delete-orphan")
    violation_scores = db.relationship("ViolationScore", back_populates="tender",
                                        cascade="all, delete-orphan")
    subscriptions = db.relationship("UserSubscription", back_populates="tender",
                                    cascade="all, delete-orphan")


class TenderChange(db.Model):
    __tablename__ = 'tender_changes'

    id = Column(Integer, primary_key=True)
    tender_id = Column(String(50), ForeignKey('tenders.id'), nullable=False)
    change_date = Column(DateTime(timezone=True), nullable=False)
    field_name = Column(String(50), nullable=False)
    old_value = Column(String)
    new_value = Column(String)

    # Relationship
    tender = db.relationship("Tender", back_populates="changes")