import pytest
from flask import Flask, redirect, url_for
from unittest.mock import MagicMock, patch
from services.auth_service import AuthService
from repositories.user_repository import UserRepository


class MockUser:
    def __init__(self, id, email, password):
        self.id = id
        self.email = email
        self._password_hash = password

    @property
    def password_hash(self):
        return self._password_hash


class TestAuthService:

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config['JWT_SECRET_KEY'] = 'test_secret'
        app.config['JWT_TOKEN_LOCATION'] = ['cookies']
        app.config['JWT_COOKIE_CSRF_PROTECT'] = False
        app.config['SERVER_NAME'] = 'localhost.test'

        @app.route('/')
        def index():
            return "OK"

        return app

    @pytest.fixture
    def mock_user_repository(self):
        return MagicMock(spec=UserRepository)

    @pytest.fixture
    def mock_password_service(self):
        password_service = MagicMock()
        password_service.check_password = MagicMock(return_value=True)
        return password_service

    @pytest.fixture
    def auth_service(self, app, mock_user_repository, mock_password_service):
        return AuthService(app=app, user_repository=mock_user_repository, password_service=mock_password_service)

    @pytest.fixture(params=[
        (1, "test@example.com", "password123"),
        (2, "test2@example.com", "another_password")
    ])
    def mock_user(self, request):
        id, email, password = request.param
        return MockUser(id, email, password)

    def test_register_user_success(self, auth_service, mock_user_repository):
        """Test successful user registration."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        mock_user_repository.get_by_email.return_value = None

        # Act
        user = auth_service.register_user(email, password)

        # Assert
        mock_user_repository.get_by_email.assert_called_once_with(email)
        mock_user_repository.add.assert_called_once()
        mock_user_repository.commit.assert_called_once()

    def test_register_user_duplicate_email(self, auth_service, mock_user_repository):
        """Test registration with an email that already exists."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        mock_user_repository.get_by_email.return_value = {'email': email}

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            auth_service.register_user(email, password)
        assert str(excinfo.value) == "User with this email already exists"

        mock_user_repository.get_by_email.assert_called_once_with(email)

    @patch('flask.redirect')
    @patch('flask.url_for')
    def test_login_success(self, mock_url_for, mock_redirect, app, auth_service, mock_user_repository, mock_user,
                           mock_password_service):
        """Test successful login."""
        # Arrange
        email = mock_user.email
        password = "password123"
        mock_user_repository.get_by_email.return_value = mock_user
        mock_password_service.check_password.return_value = True
        mock_url_for.return_value = '/index'
        mock_redirect.return_value = MagicMock()

        # Act
        with app.app_context():
            result = auth_service.login(email, password)

        # Assert
        mock_user_repository.get_by_email.assert_called_once_with(email)
        mock_password_service.check_password.assert_called_once_with(mock_user.password_hash, password)

    def test_login_invalid_credentials(self, auth_service, mock_user_repository):
        """Test login with invalid credentials (user not found)."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        mock_user_repository.get_by_email.return_value = None

        # Act
        result = auth_service.login(email, password)

        # Assert
        mock_user_repository.get_by_email.assert_called_once_with(email)
        assert result is None

    def test_login_incorrect_password(self, auth_service, mock_user_repository):
        """Test login with incorrect password."""
        # Arrange
        email = "test@example.com"
        password = "wrong_password"
        mock_user = MockUser(35, email, 'password123')
        mock_user_repository.get_by_email.return_value = mock_user

        auth_service.password_service.check_password.return_value = False

        # Act
        result = auth_service.login(email, password)

        # Assert
        mock_user_repository.get_by_email.assert_called_once_with(email)
        assert result is None