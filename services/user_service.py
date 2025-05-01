from models import User
from repositories.tender_repository import TenderRepository
from repositories.user_repository import UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository, tender_repository: TenderRepository):
        self.user_repository = user_repository
        self.tender_repository = tender_repository

    def get_user(self, user_id: int) -> User:
        """Retrieves a user by ID."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        return user

    def _user_exists(self, user_id: int) -> bool:
        """Checks if a user exists."""
        return self.user_repository.exists_by_id(user_id)

    def _tender_exists(self, tender_id: str) -> bool:
        """Checks if a tender exists."""
        return self.tender_repository.exists_by_id(tender_id)

    def delete_user(self, user_id: int) -> None:
        """Deletes a user and their subscriptions."""
        user_exists = self._user_exists(user_id)
        if not user_exists:
            return
        self.user_repository.delete_user(user_id)

    def subscribe_to_tender(self, user_id: int, tender_id: str) -> None:
        """Subscribes a user to a tender."""
        user_exists = self._user_exists(user_id)
        tender_exists = self._tender_exists(tender_id)

        if not user_exists:
            raise ValueError("User not found")
        if not tender_exists:
            raise ValueError("Tender not found")

        existing_subscription = self.user_repository.find_subscription(user_id, tender_id)

        if existing_subscription:
            raise ValueError("User is already subscribed to this tender")

        self.user_repository.add_subscription(user_id, tender_id)

    def unsubscribe_from_tender(self, user_id: int, tender_id: str) -> None:
        """Unsubscribes a user from a tender."""
        user_exists = self._user_exists(user_id)
        tender_exists = self._tender_exists(tender_id)

        if not user_exists:
            raise ValueError("User not found")
        if not tender_exists:
            raise ValueError("Tender not found")

        subscription = self.user_repository.find_subscription(user_id, tender_id)
        if not subscription:
            raise ValueError("Subscription not found")

        self.user_repository.remove_subscription(user_id, tender_id)