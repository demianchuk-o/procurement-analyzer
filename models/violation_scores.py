from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Numeric

from db import db


class ViolationScore(db.Model):
    __tablename__ = 'violation_scores'

    id = Column(Integer, primary_key=True)
    tender_id = Column(String(50), ForeignKey('tenders.id'), nullable=False)
    discriminatory_requirements_score = Column(Numeric(5, 3))
    unjustified_high_price_score = Column(Numeric(5, 3))
    tender_documentation_issues_score = Column(Numeric(5, 3))
    procedural_violations_score = Column(Numeric(5, 3))
    technical_specification_issues_score = Column(Numeric(5, 3))
    date_calculated = Column(DateTime(timezone=True), default=db.func.now(), nullable=False)

    # Relationship
    tender = db.relationship("Tender", back_populates="violation_score")

