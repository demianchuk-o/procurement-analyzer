import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from celery import Celery
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import db
from config import Config
from models import Base, Tender, Complaint, ViolationScore
from repositories.tender_repository import TenderRepository
from repositories.violation_score_repository import ViolationScoreRepository
from services.crawler_service import CrawlerService
from services.data_processor import DataProcessor
from services.complaint_analysis_service import ComplaintAnalysisService


class TestCrawlerDataProcessorIntegration:
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

    @pytest.fixture
    def violation_score_repository(self, db_session):
        return ViolationScoreRepository(db_session)

    @pytest.fixture
    def complaint_analysis_service(self, violation_score_repository):
        return ComplaintAnalysisService(violation_score_repository)

    @pytest.fixture
    def data_processor(self, tender_repository):
        return DataProcessor(tender_repo=tender_repository)

    @pytest.fixture
    def crawler_service(self, tender_repository, data_processor):
        crawler = CrawlerService(tender_repo=tender_repository)
        crawler.data_processor = data_processor
        crawler.discovery_client = MagicMock()
        crawler.legacy_client = MagicMock()
        return crawler

    @pytest.fixture(scope="session")
    def celery_app(self):
        """Create a Celery app instance."""
        app = Celery('test_tasks', broker=Config.CELERY_BROKER_URL)
        app.config_from_object('celeryconfig')
        return app

    @pytest.fixture(autouse=True)
    def setup_celery(self, celery_app):
        """Configure Celery for eager execution during tests."""
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagate = True

    def test_crawler_data_processor_integration_new_tender(self, crawler_service, tender_repository, db_session):
        """Test the integration of crawler and data processor for a new tender.
        Ensures that the new tender is created and
        that the general classifier is set correctly."""
        # Arrange
        tender_ocid = "ocid-integration-new"
        tender_uuid = "tender-uuid-integration-new"
        date_created = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        date_modified = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        crawler_service.discovery_client.fetch_tender_bridge_info.return_value = {
            'id': tender_uuid,
            'dateModified': date_modified,
            'generalClassifier': {'scheme': 'ДК-021', 'description': 'Роботи'}
        }
        crawler_service.legacy_client.fetch_tender_details.return_value = {
            'id': tender_uuid,
            'date': date_created.isoformat(),
            'dateModified': date_modified.isoformat(),
            'title': 'Integration Test Tender',
            'value': {'amount': 50000}
        }

        # Act
        result = crawler_service.sync_single_tender(tender_ocid)

        # Assert
        assert result is True

        # tender creation
        tender = tender_repository.get_by_id(tender_uuid)
        assert tender is not None
        assert tender.title == 'Integration Test Tender'
        assert tender.ocid == tender_ocid

        # general classifier creation
        assert tender.general_classifier is not None
        assert tender.general_classifier.scheme == 'ДК-021'
        assert tender.general_classifier.description == 'Роботи'

    def test_crawler_data_processor_integration_complaint_analysis(self, crawler_service, tender_repository,
                                                                   violation_score_repository,
                                                                   complaint_analysis_service, db_session):
        """Test the integration including complaint analysis.
        Ensures that the new complaint is created and processed correctly."""
        # Arrange
        tender_ocid = "ocid-integration-compl"
        tender_uuid = "tender-uuid-integration-compl"
        date_created = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        date_modified = datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc)

        crawler_service.discovery_client.fetch_tender_bridge_info.return_value = {
            'id': tender_uuid,
            'dateModified': date_modified,
            'generalClassifier': {'scheme': 'ДК-021', 'description': 'Послуги'}
        }
        crawler_service.legacy_client.fetch_tender_details.return_value = {
            'id': tender_uuid,
            'date': date_created.isoformat(),
            'dateModified': date_modified.isoformat(),
            'title': 'Tender with Complaint',
            'value': {'amount': 100000},
            "complaints": [
                {
                    "id": "complaint-1",
                    "date": "2025-01-03T10:00:00Z",
                    "description": "Це скарга зі словом дискримінаційний.",
                    "status": "pending",
                    "type": "complaint"
                }
            ]
        }

        # Act
        result = crawler_service.sync_single_tender(tender_ocid)

        # Assert
        assert result is True

        # tender and complaint creation
        tender = tender_repository.get_by_id(tender_uuid)
        assert tender is not None
        complaint = tender_repository.get_complaint_by_id("complaint-1")
        assert complaint is not None
        assert complaint.description == "Це скарга зі словом дискримінаційний."

        # violation score is updated
        violation_score = violation_score_repository.get_by_tender_id(tender_uuid)
        assert violation_score is not None
        assert violation_score.discriminatory_requirements_score == 1

        # highlighted keywords
        assert complaint.highlighted_keywords is not None
        assert len(complaint.highlighted_keywords) > 0
        assert complaint.highlighted_keywords[0]["Keyword"] == "дискримінаційний"
        assert complaint.highlighted_keywords[0]["Domain"] == "discriminatory_requirements"