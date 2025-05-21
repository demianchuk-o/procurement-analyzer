import pytest
from flask import Flask
from sqlalchemy.orm import sessionmaker

from config import Config
from db import db as flask_db
from repositories.tender_repository import TenderRepository

import flask
from flask import url_for as real_url_for


class BaseIntegrationTest:
    @pytest.fixture(autouse=True)
    def patch_url_for(self, monkeypatch):
        def fake_url_for(endpoint, **values):
            if endpoint == "index":
                return "/index"
            return real_url_for(endpoint, **values)

        monkeypatch.setattr(flask, "url_for", fake_url_for)

    @pytest.fixture(scope="session")
    def app(self):
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
        app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
        flask_db.init_app(app)

        @app.route('/index')
        def index():
            return "OK"

        return app

    @pytest.fixture(scope="session")
    def engine(self, app):
        with app.app_context():
            flask_db.create_all()
            yield flask_db.engine
            flask_db.drop_all()

    @pytest.fixture(scope="session")
    def Session(self, engine):
        return sessionmaker(bind=engine)

    @pytest.fixture
    def db_session(self, Session, app):
        with app.app_context():
            session = Session()
            try:
                yield session
            finally:
                session.close()

    @pytest.fixture
    def tender_repository(self, db_session):
        return TenderRepository(db_session)