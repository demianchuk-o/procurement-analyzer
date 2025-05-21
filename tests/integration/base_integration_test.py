import pytest
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import Config
from models import Base
from repositories.tender_repository import TenderRepository


class BaseIntegrationTest:
    @pytest.fixture(scope="session")
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