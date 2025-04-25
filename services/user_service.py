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

    def get_tender(self, tender_id: str):
        """Retrieves a tender by ID."""
        tender = self.tender_repository.get_by_id(tender_id)
        if not tender:
            raise ValueError("Tender not found")
        return tender

    def delete_user(self, user_id: int) -> None:
        """Deletes a user and their subscriptions."""
        user = self.get_user(user_id)
        self.user_repository.delete_user(user.id)

    def subscribe_to_tender(self, user_id: int, tender_id: str) -> None:
        """Subscribes a user to a tender."""
        user = self.get_user(user_id)

        tender = self.get_tender(tender_id)

        existing_subscription = self.user_repository.find_subscription(user_id, tender_id)

        if existing_subscription:
            raise ValueError("User is already subscribed to this tender")

        self.user_repository.add_subscription(user_id, tender_id)

    def unsubscribe_from_tender(self, user_id: int, tender_id: str) -> None:
        """Unsubscribes a user from a tender."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        tender = self.get_tender(tender_id)

        subscription = self.user_repository.find_subscription(user.id, tender.id)
        if not subscription:
            raise ValueError("Subscription not found")

        self.user_repository.remove_subscription(user.id, tender.id)