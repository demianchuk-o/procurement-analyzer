import pytest
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import Config
from db import db
from models import Base
from repositories.tender_repository import TenderRepository
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.password_service import PasswordService
from services.user_service import UserService


class BaseIntegrationTest:
    @pytest.fixture(scope="session")
    def app(self):
        app = Flask(__name__)
        app.config.from_object(Config)
        db.init_app(app)
        return app

    @pytest.fixture(scope="session")
    def engine(self, app):
        """Create a SQLAlchemy engine for the test database."""
        with app.app_context():
            engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
            Base.metadata.create_all(engine)
            yield engine
            Base.metadata.drop_all(engine)
            Base.metadata.drop_all(engine)

    @pytest.fixture(scope="session")
    def Session(self, engine):
        """Create a SQLAlchemy session factory."""
        return sessionmaker(bind=engine)

    @pytest.fixture
    def db_session(self, Session, app):
        """Provide a session for each test function."""
        with app.app_context():
            session = Session()
            try:
                yield session
            finally:
                session.close()

    @pytest.fixture
    def tender_repository(self, db_session):
        return TenderRepository(db_session)