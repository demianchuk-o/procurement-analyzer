from sqlalchemy import Column, String, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from db import db


class GeneralClassifier(db.Model):
    __tablename__ = 'general_classifiers'

    # make id autoincrement
    id = Column(Integer, primary_key=True, autoincrement=True)
    scheme = Column(String, nullable=False)
    description = Column(String, nullable=False)

    # Relationships
    tenders = relationship("Tender", back_populates="general_classifier")

    __table_args__ = (UniqueConstraint('scheme', 'description', name='uq_scheme_description'),)

