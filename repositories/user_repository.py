import hashlib
from typing import Optional

from sqlalchemy.orm import Session

from models import User, UserSubscription
from repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: Session):
        super().__init__(session)

    def get_by_id(self, id: int) -> Optional[User]:
        return self._session.get(User, id)

    def get_by_email(self, email: str) -> Optional[User]:
        """Gets a user by their hashed email."""
        return self._session.query(User).filter(User.email == email).first()

    def delete_user(self, user_id: int) -> bool:
        """Deletes a user by their ID, committing the changes."""
        user = self.get_by_id(user_id)
        if user:
            self._session.delete(user)
            self._session.commit()
            return True
        else:
            return False

    def find_subscription(self, user_id: int, tender_id: str) -> Optional[UserSubscription]:
        """Finds a subscription for a user on a specific tender."""
        return self._session.query(UserSubscription).filter_by(user_id=user_id, tender_id=tender_id).first()

    def find_user_subscriptions(self, user_id: int) -> list[UserSubscription]:
        """Finds all subscriptions for a user."""
        return self._session.query(UserSubscription).filter_by(user_id=user_id).all()

    def add_subscription(self, user_id: int, tender_id: str) -> None:
        """Adds a subscription for a user."""
        subscription = UserSubscription(user_id=user_id, tender_id=tender_id)
        self._session.add(subscription)
        self._session.commit()

    def remove_subscription(self, user_id: int, tender_id: str) -> None:
        """Removes a subscription for a user."""
        subscription = self.find_subscription(user_id, tender_id)
        if subscription:
            self._session.delete(subscription)
            self._session.commit()