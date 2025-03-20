from sqlalchemy import Column, Text, String, Integer
from sqlalchemy.orm import relationship

from db import db


class ItemClassification(db.Model):
    __tablename__ = 'item_classifications'

    id = Column(String(32), primary_key=True)
    scheme = Column(String, nullable=False)
    description = Column(String, nullable=False)

    # Relationships
    tenders = relationship("Tender", back_populates="item_classification")

