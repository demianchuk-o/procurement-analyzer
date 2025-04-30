import pytest
from unittest.mock import MagicMock

from repositories.tender_repository import TenderRepository
from repositories.user_repository import UserRepository
from services.user_service import UserService


class TestUserService:

    @pytest.fixture
    def mock_user_repository(self):
        return MagicMock(spec=UserRepository)

    @pytest.fixture
    def mock_tender_repository(self):
        return MagicMock(spec=TenderRepository)

    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    @pytest.fixture
    def user_service(self, mock_user_repository, mock_tender_repository):
        return UserService(user_repository=mock_user_repository,
                           tender_repository=mock_tender_repository)

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

    def test_delete_user_success(self, user_service, mock_user_repository):
        """Test deleting a user successfully."""
        # Arrange
        user_id = 123
        mock_user = MagicMock(id=user_id)
        mock_user_repository.get_by_id.return_value = mock_user

        # Act
        user_service.delete_user(user_id)

        # Assert
        mock_user_repository.get_by_id.assert_called_once_with(user_id)
        mock_user_repository.delete_user.assert_called_once_with(user_id)

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

    def test_subscribe_to_tender_success(self, user_service, mock_user_repository, mock_tender_repository):
        """Test subscribing a user to a tender successfully."""
        # Arrange
        user_id = 123
        tender_id = "tender123"
        mock_user_repository.exists_by_id.return_value = True
        mock_tender_repository.exists_by_id.return_value = True
        mock_user_repository.find_subscription.return_value = None

        # Act
        user_service.subscribe_to_tender(user_id, tender_id)

        # Assert
        mock_user_repository.exists_by_id.assert_called_once_with(user_id)
        mock_tender_repository.exists_by_id.assert_called_once_with(tender_id)
        mock_user_repository.add_subscription.assert_called_once_with(user_id, tender_id)

    def test_subscribe_to_tender_user_not_found(self, user_service, mock_user_repository):
        """Test subscribing a user to a tender when the user does not exist."""
        # Arrange
        user_id = 123
        tender_id = "tender123"
        mock_user_repository.exists_by_id.return_value = False

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            user_service.subscribe_to_tender(user_id, tender_id)
        assert str(excinfo.value) == "User not found"
        mock_user_repository.exists_by_id.assert_called_once_with(user_id)

    def test_unsubscribe_from_tender_success(self, user_service, mock_user_repository, mock_tender_repository):
        """Test unsubscribing a user from a tender successfully."""
        # Arrange
        user_id = 123
        tender_id = "tender123"

        mock_user_repository.exists_by_id.return_value = True
        mock_tender_repository.exists_by_id.return_value = True
        mock_subscription = MagicMock(user_id, tender_id)
        mock_user_repository.find_subscription.return_value = mock_subscription

        # Act
        user_service.unsubscribe_from_tender(user_id, tender_id)

        # Assert
        mock_user_repository.exists_by_id.assert_called_once_with(user_id)
        mock_tender_repository.exists_by_id.assert_called_once_with(tender_id)
        mock_user_repository.find_subscription.assert_called_once_with(user_id, tender_id)
        mock_user_repository.remove_subscription.assert_called_once_with(user_id, tender_id)

    def test_unsubscribe_from_tender_user_not_found(self, user_service, mock_user_repository):
        """Test unsubscribing a user from a tender when the user does not exist."""
        # Arrange
        user_id = 123
        tender_id = "tender123"
        mock_user_repository.exists_by_id.return_value = False

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            user_service.unsubscribe_from_tender(user_id, tender_id)
        assert str(excinfo.value) == "User not found"
        mock_user_repository.exists_by_id.assert_called_once_with(user_id)

    def test_unsubscribe_from_tender_subscription_not_found(self, user_service, mock_user_repository, mock_tender_repository):
        """Test unsubscribing a user from a tender when the subscription does not exist."""
        # Arrange
        user_id = 123
        tender_id = "tender123"
        mock_user_repository.exists_by_id.return_value = True
        mock_tender_repository.exists_by_id.return_value = True
        mock_user_repository.find_subscription.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            user_service.unsubscribe_from_tender(user_id, tender_id)
        assert str(excinfo.value) == "Subscription not found"
        mock_user_repository.exists_by_id.assert_called_once_with(user_id)
        mock_tender_repository.exists_by_id.assert_called_once_with(tender_id)
        mock_user_repository.find_subscription.assert_called_once_with(user_id, tender_id)