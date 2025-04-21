import hashlib
from typing import Optional

from sqlalchemy.orm import Session

from models import User
from repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: Session):
        super().__init__(session)

    def get_by_id(self, id: int) -> Optional[User]:
        return self._session.get(User, id)

    def get_by_email(self, email_hash: str) -> Optional[User]:
        """Gets a user by their hashed email."""
        return self._session.query(User).filter(User.email == email_hash).first()

    def hash_email(self, email: str) -> str:
        """Hashes the email using SHA-256."""
        return hashlib.sha256(email.encode()).hexdigest()