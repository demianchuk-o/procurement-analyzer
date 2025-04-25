from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug.security import generate_password_hash

from db import db


class User(db.Model):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_hash = Column(String, unique=True, nullable=False)
    _password_hash = Column(String(255), nullable=False)

    # Properties
    @hybrid_property
    def password_hash(self):
        return self._password_hash

    @password_hash.setter
    def password_hash(self, password):
        self._password_hash = generate_password_hash(password)

    # Relationships
    subscriptions = db.relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")