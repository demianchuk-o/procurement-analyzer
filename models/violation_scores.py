from sqlalchemy import Column, String, ForeignKey, Integer, JSON

from db import db


class ViolationScore(db.Model):
    __tablename__ = 'violation_scores'

    id = Column(Integer, primary_key=True)
    tender_id = Column(String(50), ForeignKey('tenders.id'), nullable=False)
    scores = Column(JSON)

    # Relationship
    tender = db.relationship("Tender", back_populates="violation_score")

