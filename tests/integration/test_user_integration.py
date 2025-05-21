import pytest
from flask import url_for
from sqlalchemy.orm.exc import NoResultFound
from datetime import datetime, timezone

from models import User, UserSubscription, Tender
from repositories.user_repository import UserRepository
from services.password_service import PasswordService
from services.user_service import UserService
from services.auth_service import AuthService
from tests.integration.base_integration_test import BaseIntegrationTest


class TestUserIntegration(BaseIntegrationTest):
    @pytest.fixture
    def user_repository(self, db_session):
        """UserRepository fixture."""
        return UserRepository(db_session)

    @pytest.fixture
    def password_service(self):
        """PasswordService fixture."""
        return PasswordService()

    @pytest.fixture
    def auth_service(self, app, user_repository, password_service):
        """AuthService fixture."""
        return AuthService(app, user_repository, password_service)

    @pytest.fixture
    def user_service(self, user_repository, tender_repository):
        """UserService fixture."""
        return UserService(user_repository, tender_repository)

    def create_test_user(self, user_repository, email="test@example.com"):
        """Creates a test user with a unique email."""
        user = User(email=email)
        user.password_hash = "password"
        user_repository.add(user)
        user_repository.commit()
        return user

    def create_test_tender(self, tender_repository, tender_uuid="tender-uuid-integration-update--", tender_ocid="ocid-integration-updat"):
        """Creates a test tender with a unique id and ocid."""
        date_created = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        date_modified_initial = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        tender = Tender(
            id=tender_uuid,
            ocid=tender_ocid,
            date_created=date_created,
            date_modified=date_modified_initial,
            title='Initial Tender Title',
            value_amount=50000,
            status='active'
        )
        tender_repository.add(tender)
        tender_repository.commit()
        return tender

    def test_user_registration(self, user_repository, auth_service):
        """Test successful user registration."""
        # Arrange
        email = "new_user_unique@example.com"
        password = "password"

        # Act
        user = auth_service.register_user(email, password)

        # Assert
        assert user is not None
        assert user_repository.get_by_email(email) is not None

    def test_user_registration_duplicate_email(self, auth_service):
        """Test registration with duplicate email."""
        # Arrange
        email = "duplicate_user@example.com"
        password = "password"
        auth_service.register_user(email, password)

        # Act & Assert
        with pytest.raises(ValueError):
            auth_service.register_user(email, password)

    def test_user_login_success(self, app, user_repository, auth_service, password_service):
        # Arrange
        email = "login_user@example.com"
        password = "password"
        self.create_test_user(user_repository, email=email)

        # Act
        with app.test_request_context():
            response = auth_service.login(email, password)

        # Assert
        assert response.status_code == 302
        assert response.location == "/index"
        assert "access_token_cookie=" in response.headers.get("Set-Cookie", "")

    def test_user_login_incorrect_password(self, auth_service, user_repository):
        """Test login with incorrect password."""
        # Arrange
        email = "incorrect_password_user@example.com"
        password = "password"
        wrong_password = "wrong_password"
        test_user = self.create_test_user(user_repository, email=email)

        # Act
        user = auth_service.login(email, wrong_password)

        # Assert
        assert user is None

    def test_user_deletion(self, user_service, user_repository):
        """Test successful user deletion."""
        # Arrange
        email = "deletion_user@example.com"
        test_user = self.create_test_user(user_repository, email=email)
        user_id = test_user.id

        # Act
        user_service.delete_user(user_id)

        # Assert
        deleted_user = user_repository.get_by_id(user_id)
        assert deleted_user is None


    def test_subscribe_to_tender(self, user_service, user_repository, tender_repository):
        """Test subscribing a user to a tender."""
        # Arrange
        email = "subscribe_user@example.com"
        test_user = self.create_test_user(user_repository, email=email)
        tender_uuid = "tender-subscribe"
        tender_ocid = "ocid-subscribe"
        test_tender = self.create_test_tender(tender_repository, tender_uuid=tender_uuid, tender_ocid=tender_ocid)
        user_id = test_user.id
        tender_id = test_tender.id

        # Act
        user_service.subscribe_to_tender(user_id, tender_id)

        # Assert
        subscription = user_repository.find_subscription(user_id, tender_id)
        assert subscription is not None
        assert subscription.user_id == user_id
        assert subscription.tender_id == tender_id

    def test_subscribe_to_tender_twice(self, user_service, user_repository, tender_repository):
        """Test subscribing a user to the same tender twice."""
        # Arrange
        email = "subscribe_twice_user@example.com"
        test_user = self.create_test_user(user_repository, email=email)
        tender_uuid = "tender-subscribe-twice"
        tender_ocid = "ocid-subscribe-twice"
        test_tender = self.create_test_tender(tender_repository, tender_uuid=tender_uuid, tender_ocid=tender_ocid)
        user_id = test_user.id
        tender_id = test_tender.id
        user_service.subscribe_to_tender(user_id, tender_id)

        # Act
        with pytest.raises(ValueError) as excinfo:
            user_service.subscribe_to_tender(user_id, tender_id)

        # Assert
        assert str(excinfo.value) == "User is already subscribed to this tender"

        subscriptions = user_repository.find_user_subscriptions(user_id)
        assert len(subscriptions) == 1

    def test_subscribe_non_existent_user(self, user_service, tender_repository):
        """Test subscribing a non-existent user."""
        # Arrange
        user_id = 9999  # Non-existent user ID
        tender_uuid = "tender-subscribe-user-not-exists"
        tender_ocid = "ocid-user-not-exists"
        test_tender = self.create_test_tender(tender_repository, tender_uuid=tender_uuid, tender_ocid=tender_ocid)
        tender_id = test_tender.id

        # Act & Assert
        with pytest.raises(ValueError):
            user_service.subscribe_to_tender(user_id, tender_id)

    def test_subscribe_non_existent_tender(self, user_service, user_repository):

        """Test subscribing to a non-existent tender."""
        # Arrange
        email = "subscribe_non_existent_tender@example.com"
        test_user = self.create_test_user(user_repository, email=email)
        user_id = test_user.id
        tender_id = "9999"  # Non-existent tender ID

        # Act & Assert
        with pytest.raises(ValueError):
            user_service.subscribe_to_tender(user_id, tender_id)

    def test_unsubscribe_from_tender(self, user_service, user_repository, tender_repository):
        """Test unsubscribing a user from a tender."""
        # Arrange
        email = "unsubscribe_user@example.com"
        test_user = self.create_test_user(user_repository, email=email)
        tender_uuid = "tender-unsubscribe"
        tender_ocid = "ocid-unsubscribe"
        test_tender = self.create_test_tender(tender_repository, tender_uuid=tender_uuid, tender_ocid=tender_ocid)
        user_id = test_user.id
        tender_id = test_tender.id

        user_service.subscribe_to_tender(user_id, tender_id)

        # Act
        user_service.unsubscribe_from_tender(user_id, tender_id)

        # Assert
        subscription = user_repository.find_subscription(user_id, tender_id)
        assert subscription is None

    def test_unsubscribe_non_existent_user(self, user_service, tender_repository):
        """Test unsubscribing a non-existent user."""
        # Arrange
        user_id = 9999
        tender_uuid = "tender-unsub-user-not-exists"
        tender_ocid = "ocid-unsub-user-not-ex"
        test_tender = self.create_test_tender(tender_repository, tender_uuid=tender_uuid, tender_ocid=tender_ocid)
        tender_id = test_tender.id

        # Act & Assert
        with pytest.raises(ValueError):
            user_service.unsubscribe_from_tender(user_id, tender_id)

    def test_unsubscribe_non_existent_tender(self, user_service, user_repository):
        """Test unsubscribing from a non-existent tender."""
        # Arrange
        email = "unsubscribe_non_existent_tender@example.com"
        test_user = self.create_test_user(user_repository, email=email)
        user_id = test_user.id
        tender_id = "9999"  # Non-existent tender ID

        # Act & Assert
        with pytest.raises(ValueError):
            user_service.unsubscribe_from_tender(user_id, tender_id)

    def test_unsubscribe_when_not_subscribed(self, user_service, user_repository, tender_repository):
        """Test unsubscribing when the user is not subscribed to the tender."""
        # Arrange
        email = "unsubscribe_not_subscribed@example.com"
        test_user = self.create_test_user(user_repository, email=email)
        tender_uuid = "tender-unsub-not-subbed"
        tender_ocid = "ocid-unsub-not-subbed"
        test_tender = self.create_test_tender(tender_repository, tender_uuid=tender_uuid, tender_ocid=tender_ocid)
        user_id = test_user.id
        tender_id = test_tender.id

        # Act
        with pytest.raises(ValueError) as excinfo:
            user_service.unsubscribe_from_tender(user_id, tender_id)

        # Assert
        assert str(excinfo.value) == "Subscription not found"
        subscription = user_repository.find_subscription(user_id, tender_id)
        assert subscription is None