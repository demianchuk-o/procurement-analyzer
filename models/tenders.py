from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Numeric

from db import db


class Tender(db.Model):
    __tablename__ = 'tenders'

    # core data
    id = Column(String(32), primary_key=True) # 32-char UUID
    ocid = Column(String(22), nullable=False)
    date_created = Column(DateTime(timezone=True), nullable=False)
    date_modified = Column(DateTime(timezone=True), nullable=False)
    title = Column(Text, nullable=False)
    value_amount = Column(Numeric(18, 2))
    status = Column(String)

    # periods
    enquiry_period_start_date = Column(DateTime(timezone=True))
    enquiry_period_end_date = Column(DateTime(timezone=True))
    tender_period_start_date = Column(DateTime(timezone=True))
    tender_period_end_date = Column(DateTime(timezone=True))
    auction_period_start_date = Column(DateTime(timezone=True))
    auction_period_end_date = Column(DateTime(timezone=True))
    award_period_start_date = Column(DateTime(timezone=True))
    award_period_end_date = Column(DateTime(timezone=True))
    notice_publication_date = Column(DateTime(timezone=True))

    # classifier
    general_classifier_id = Column(Integer, ForeignKey('general_classifiers.id'))

    # Relationships
    general_classifier = db.relationship("GeneralClassifier", back_populates="tenders")
    awards = db.relationship("Award", back_populates="tender",
                            cascade="all, delete-orphan")
    bids = db.relationship("Bid", back_populates="tender",
                            cascade="all, delete-orphan")
    complaints = db.relationship("Complaint", back_populates="tender",
                                 cascade="all, delete-orphan")
    documents = db.relationship("TenderDocument", back_populates="tender",
                                 cascade="all, delete-orphan")
    changes = db.relationship("TenderChange", back_populates="tender",
                              order_by="TenderChange.change_date",
                              cascade="all, delete-orphan")
    violation_score = db.relationship("ViolationScore", back_populates="tender",
                                     cascade="all, delete-orphan")


class TenderChange(db.Model):
    __tablename__ = 'tender_changes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tender_id = Column(String(50), ForeignKey('tenders.id'), nullable=False)
    change_date = Column(DateTime(timezone=True), nullable=False)
    field_name = Column(String(50), nullable=False)
    old_value = Column(String)
    new_value = Column(String)

    # Relationship
    tender = db.relationship("Tender", back_populates="changes")