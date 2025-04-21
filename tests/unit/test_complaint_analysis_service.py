import pytest
from unittest.mock import MagicMock

from models.complaints import Complaint
from repositories.violation_score_repository import ViolationScoreRepository
from services.complaint_analysis_service import ComplaintAnalysisService


def create_complaint_analysis_service(mock_violation_score_repo, mocker) -> ComplaintAnalysisService:
    keywords = {
        "discriminatory_requirements": ["дискримінаційний"],
        "unjustified_high_price": ["дорогий"],
    }

    mock_load_keywords = MagicMock(return_value=keywords)
    mocker.patch("services.complaint_analysis_service.ComplaintAnalysisService._load_keywords",
                 new=mock_load_keywords)

    service = ComplaintAnalysisService(mock_violation_score_repo, keywords_path='dummy_path')
    return service


class TestComplaintAnalysisService:

    @pytest.fixture
    def mock_violation_score_repo_existing_score(self):
        mock_repo = MagicMock(spec=ViolationScoreRepository)
        mock_existing_score = MagicMock()
        mock_existing_score.discriminatory_requirements_score = 0
        mock_existing_score.unjustified_high_price_score = 0
        mock_existing_score.tender_documentation_issues_score = 0
        mock_existing_score.procedural_violations_score = 0
        mock_existing_score.technical_specification_issues_score = 0
        mock_repo.get_by_tender_id.return_value = mock_existing_score
        mock_repo.flush = MagicMock()
        mock_repo.commit = MagicMock()
        return mock_repo

    @pytest.fixture
    def mock_violation_score_repo(self):
        mock_repo = MagicMock(spec=ViolationScoreRepository)
        mock_repo.get_by_tender_id.return_value = None
        return mock_repo

    @pytest.fixture
    def complaint_analysis_service(self, mock_violation_score_repo, mocker):
        return create_complaint_analysis_service(mock_violation_score_repo, mocker)

    @pytest.fixture
    def complaint_analysis_service_existing_score(self, mock_violation_score_repo_existing_score, mocker):
        return create_complaint_analysis_service(mock_violation_score_repo_existing_score, mocker)

    def test_analyze_complaint_text_keyword_found(self, complaint_analysis_service):
        """Test when the keyword is found in the complaint text."""
        text = "Це дискримінаційний приклад."
        result = complaint_analysis_service.analyze_complaint_text(text)

        assert len(result) == 1
        assert result[0]["Keyword"] == "дискримінаційний"
        assert result[0]["Domain"] == "discriminatory_requirements"
        assert result[0]["StartPosition"] == 3
        assert result[0]["Length"] == len("дискримінаційний")

    def test_analyze_complaint_text_keyword_not_found(self, complaint_analysis_service):
        """Test when the keyword is not found in the complaint text."""
        text = "Текст без ключових слів."
        result = complaint_analysis_service.analyze_complaint_text(text)
        assert len(result) == 0

    def test_update_violation_scores_existing_score(self, complaint_analysis_service_existing_score,
                                                    mock_violation_score_repo_existing_score):
        """Test updating violation scores when an existing score exists."""
        tender_id = "tender123"
        complaint = Complaint(id="complaint1", description="Це дискримінаційний приклад.")

        # Act
        result = (complaint_analysis_service_existing_score
                  .update_violation_scores(tender_id, complaint))

        # Assert
        assert result is not None
        assert result.discriminatory_requirements_score == 1
        mock_violation_score_repo_existing_score.get_by_tender_id.assert_called_once_with(tender_id)
        mock_violation_score_repo_existing_score.flush.assert_called_once()
        mock_violation_score_repo_existing_score.commit.assert_called_once()

    def test_update_violation_scores_new_score(self, complaint_analysis_service, mock_violation_score_repo):
        """Test creating violation scores when no existing score exists."""
        tender_id = "tender456"
        complaint = Complaint(id="complaint2", description="Це дискримінаційний приклад.")

        # Act
        result = complaint_analysis_service.update_violation_scores(tender_id, complaint)

        # Assert
        assert result is not None
        assert result.discriminatory_requirements_score == 1
        mock_violation_score_repo.get_by_tender_id.assert_called_once_with(tender_id)
        mock_violation_score_repo.create.assert_called_once()