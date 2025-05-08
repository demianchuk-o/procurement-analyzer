from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime, String

from db import db


class TenderDocument(db.Model):
    __tablename__ = 'tender_documents'

    id = Column(String(32), primary_key=True)
    tender_id = Column(String(32), ForeignKey('tenders.id'), nullable=False)
    document_of = Column(String)
    title = Column(String)
    format = Column(String)
    url = Column(Text)
    hash = Column(Text)
    date_published = Column(DateTime(timezone=True))
    date_modified = Column(DateTime(timezone=True))

    # Relationships
    tender = db.relationship("Tender", back_populates="documents")
    changes = db.relationship("TenderDocumentChange", back_populates="document",
                              cascade="all, delete-orphan")



class TenderDocumentChange(db.Model):
    __tablename__ = 'tender_document_changes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(32), ForeignKey('tender_documents.id'), nullable=False)
    tender_id = Column(String(32), ForeignKey('tenders.id'), nullable=False)
    change_date = Column(DateTime(timezone=True), nullable=False)
    field_name = Column(String(50), nullable=False)
    old_value = Column(String)
    new_value = Column(String)

    document = db.relationship("TenderDocument", back_populates="changes")