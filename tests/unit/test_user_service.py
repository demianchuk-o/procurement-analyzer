import hashlib
from unittest.mock import MagicMock

import pytest

from models import UserSubscription
from repositories.user_repository import UserRepository
from services.user_service import UserService


class TestUserService:

    @pytest.fixture
    def mock_user_repository(self):
        return MagicMock(spec=UserRepository)

    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    @pytest.fixture
    def user_service(self, mock_session, mock_user_repository):
        return UserService(session=mock_session, user_repository=mock_user_repository)

    def test_register_user_success(self, user_service, mock_user_repository, mock_session):
        """Test successful user registration."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        mock_user_repository.get_by_email.return_value = None
        mock_user = MagicMock(email_hash=email_hash)
        mock_user_repository.add.return_value = mock_user

        # Act
        user = user_service.register_user(email, password)

        # Assert
        mock_user_repository.get_by_email.assert_called_once_with(email_hash)
        mock_user_repository.add.assert_called_once()
        assert user.email_hash == email_hash
        mock_session.commit.assert_called_once()

    def test_register_user_duplicate_email(self, user_service, mock_user_repository):
        """Test registration with an email that already exists."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        mock_user_repository.get_by_email.return_value = {'email_hash': email_hash}

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            user_service.register_user(email, password)
        assert str(excinfo.value) == "User with this email already exists"

        mock_user_repository.get_by_email.assert_called_once_with(email_hash)

    def test_get_user_success(self, user_service, mock_user_repository):
        """Test getting a user by ID successfully."""
        # Arrange
        user_id = 123
        mock_user = {'id': user_id}
        mock_user_repository.get_by_id.return_value = mock_user

        # Act
        user = user_service.get_user(user_id)

        # Assert
        mock_user_repository.get_by_id.assert_called_once_with(user_id)
        assert user['id'] == user_id

    def test_get_user_not_found(self, user_service, mock_user_repository):
        """Test getting a user by ID when the user does not exist."""
        # Arrange
        user_id = 123
        mock_user_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            user_service.get_user(user_id)
        assert str(excinfo.value) == "User not found"
        mock_user_repository.get_by_id.assert_called_once_with(user_id)

    def test_delete_user_success(self, user_service, mock_user_repository, mock_session):
        """Test deleting a user successfully."""
        # Arrange
        user_id = 123
        mock_user = {'id': user_id}
        mock_user_repository.get_by_id.return_value = mock_user

        # Act
        user_service.delete_user(user_id)

        # Assert
        mock_user_repository.get_by_id.assert_called_once_with(user_id)
        mock_session.delete.assert_called_once_with(mock_user)
        mock_session.commit.assert_called_once()

    def test_delete_user_not_found(self, user_service, mock_user_repository):
        """Test deleting a user when the user does not exist."""
        # Arrange
        user_id = 123
        mock_user_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            user_service.delete_user(user_id)
        assert str(excinfo.value) == "User not found"
        mock_user_repository.get_by_id.assert_called_once_with(user_id)

    def test_subscribe_to_tender_success(self, user_service, mock_user_repository, mock_session):
        """Test subscribing a user to a tender successfully."""
        # Arrange
        user_id = 123
        tender_id = "tender123"
        mock_user = {'id': user_id}
        mock_user_repository.get_by_id.return_value = mock_user

        # Act
        user_service.subscribe_to_tender(user_id, tender_id)

        # Assert
        mock_user_repository.get_by_id.assert_called_once_with(user_id)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_subscribe_to_tender_user_not_found(self, user_service, mock_user_repository):
        """Test subscribing a user to a tender when the user does not exist."""
        # Arrange
        user_id = 123
        tender_id = "tender123"
        mock_user_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            user_service.subscribe_to_tender(user_id, tender_id)
        assert str(excinfo.value) == "User not found"
        mock_user_repository.get_by_id.assert_called_once_with(user_id)

    def test_unsubscribe_from_tender_success(self, user_service, mock_user_repository, mock_session):
        """Test unsubscribing a user from a tender successfully."""
        # Arrange
        user_id = 123
        tender_id = "tender123"
        mock_user = {'id': user_id}
        mock_user_repository.get_by_id.return_value = mock_user
        mock_subscription = MagicMock(spec=UserSubscription, user_id=user_id, tender_id=tender_id)
        mock_subscription_query = MagicMock()
        mock_subscription_query.filter_by.return_value.first.return_value = mock_subscription
        UserSubscription.query = mock_subscription_query

        # Act
        user_service.unsubscribe_from_tender(user_id, tender_id)

        # Assert
        mock_user_repository.get_by_id.assert_called_once_with(user_id)
        mock_subscription_query.filter_by.assert_called_once_with(user_id=user_id, tender_id=tender_id)
        mock_session.delete.assert_called_once_with(mock_subscription)
        mock_session.commit.assert_called_once()

    def test_unsubscribe_from_tender_user_not_found(self, user_service, mock_user_repository):
        """Test unsubscribing a user from a tender when the user does not exist."""
        # Arrange
        user_id = 123
        tender_id = "tender123"
        mock_user_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            user_service.unsubscribe_from_tender(user_id, tender_id)
        assert str(excinfo.value) == "User not found"
        mock_user_repository.get_by_id.assert_called_once_with(user_id)

    def test_unsubscribe_from_tender_subscription_not_found(self, user_service, mock_user_repository):
        """Test unsubscribing a user from a tender when the subscription does not exist."""
        # Arrange
        user_id = 123
        tender_id = "tender123"
        mock_user = {'id': user_id}
        mock_user_repository.get_by_id.return_value = mock_user
        mock_subscription_query = MagicMock()
        mock_subscription_query.filter_by.return_value.first.return_value = None
        UserSubscription.query = mock_subscription_query

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            user_service.unsubscribe_from_tender(user_id, tender_id)
        assert str(excinfo.value) == "Subscription not found"
        mock_user_repository.get_by_id.assert_called_once_with(user_id)
        mock_subscription_query.filter_by.assert_called_once_with(user_id=user_id, tender_id=tender_id)