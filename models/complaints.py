from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime, String, JSON

from db import db


class Complaint(db.Model):
    __tablename__ = 'complaints'

    id = Column(String(32), primary_key=True)
    tender_id = Column(String(32), ForeignKey('tenders.id'), nullable=False)
    status = Column(String)
    title = Column(Text)
    description = Column(Text)
    date = Column(DateTime)
    date_submitted = Column(DateTime)
    date_answered = Column(DateTime)
    type = Column(String(50), nullable=False)
    highlighted_keywords = Column(JSON)

    # Relationships
    tender = db.relationship("Tender", back_populates="complaints")
    changes = db.relationship("ComplaintChange", back_populates="complaint",
                              cascade="all, delete-orphan")

class ComplaintChange(db.Model):
    __tablename__ = 'complaint_changes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(String(32), ForeignKey('complaints.id'), nullable=False)
    change_date = Column(DateTime(timezone=True), nullable=False)
    field_name = Column(String(50), nullable=False)
    old_value = Column(String)
    new_value = Column(String)

    #Relationships
    complaint = db.relationship("Complaint", back_populates="changes")