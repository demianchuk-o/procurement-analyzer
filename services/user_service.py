import hashlib

from sqlalchemy.orm import Session

from models import User, UserSubscription
from repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: Session, user_repository: UserRepository):
        self.session = session
        self.user_repository = user_repository

    def register_user(self, email: str, password: str) -> User:
        """Registers a new user, hashing the email and setting the password."""
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        existing_user = self.user_repository.get_by_email(email_hash)
        if existing_user:
            raise ValueError("User with this email already exists")

        user = User(email_hash=email_hash)
        user.password_hash = password
        self.user_repository.add(user)
        self.session.commit()
        return user

    def get_user(self, user_id: int) -> User:
        """Retrieves a user by ID."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        return user

    def delete_user(self, user_id: int) -> None:
        """Deletes a user and their subscriptions."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        self.session.delete(user)
        self.session.commit()

    def subscribe_to_tender(self, user_id: int, tender_id: str) -> None:
        """Subscribes a user to a tender."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        subscription = UserSubscription(user_id=user_id, tender_id=tender_id)
        self.session.add(subscription)
        self.session.commit()

    def unsubscribe_from_tender(self, user_id: int, tender_id: str) -> None:
        """Unsubscribes a user from a tender."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        subscription = UserSubscription.query.filter_by(user_id=user_id, tender_id=tender_id).first()
        if not subscription:
            raise ValueError("Subscription not found")

        self.session.delete(subscription)
        self.session.commit()