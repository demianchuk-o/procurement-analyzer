from sqlalchemy import Column, String, ForeignKey, Integer

from db import db


class UserSubscription(db.Model):
    __tablename__ = 'user_subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tender_id = Column(String(32), ForeignKey('tenders.id'), nullable=False)

    __table_args__ = (
      db.UniqueConstraint('user_id', 'tender_id', name='UK_UserSubscriptions_user_id_tender_id'),
    )

    # Relationships
    user = db.relationship("User", back_populates="subscriptions")

