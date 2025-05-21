import pytest
from unittest.mock import MagicMock
import math
from collections import namedtuple

from models.complaints import Complaint
from models import ViolationScore
from repositories.violation_score_repository import ViolationScoreRepository
from services.complaint_analysis_service import ComplaintAnalysisService

from signals import NLP_MODEL, LEMMATIZED_KEYWORDS

MockToken = namedtuple('MockToken', ['lemma_', 'idx', 'text'])


def mock_spacy_doc_processor(text_input: str):
    """
    Mocks the behavior of a spaCy Doc object for given text inputs.
    The input `text_input` to this function will be the lowercased complaint text.
    """
    tokens = []
    if text_input == "це дискримінаційний приклад.":
        tokens = [
            MockToken(lemma_='це', idx=0, text='це'),
            MockToken(lemma_='дискримінаційний', idx=3, text='дискримінаційний'),
            MockToken(lemma_='приклад', idx=20, text='приклад'),
            MockToken(lemma_='.', idx=27, text='.'),
        ]
    elif text_input == "текст без ключових слів.":
        tokens = [
            MockToken(lemma_='текст', idx=0, text='текст'),
            MockToken(lemma_='без', idx=6, text='без'),
            MockToken(lemma_='ключовий', idx=10, text='ключових'),
            MockToken(lemma_='слово', idx=19, text='слів'),
            MockToken(lemma_='.', idx=23, text='.'),
        ]

    doc_mock = MagicMock()
    doc_mock.__iter__.return_value = iter(tokens)
    return doc_mock


class TestComplaintAnalysisService:

    @pytest.fixture
    def mock_nlp_and_keywords(self, mocker):
        """Mocks NLP_MODEL and LEMMATIZED_KEYWORDS from the signals module."""
        mock_nlp = MagicMock(side_effect=mock_spacy_doc_processor)
        mocker.patch('signals.NLP_MODEL', mock_nlp)

        test_keywords = {
            "0": ["дискримінаційний"],
            "1": ["дорогий"],
        }

        mocker.patch('signals.LEMMATIZED_KEYWORDS', test_keywords)

        return mock_nlp, test_keywords

    @pytest.fixture
    def mock_violation_score_repo_existing_score(self):
        mock_repo = MagicMock(spec=ViolationScoreRepository)
        mock_existing_score = MagicMock()
        mock_existing_score.tender_id = "tender123"
        mock_existing_score.scores = {
            "0": {"score": 0.0, "keywords": {}},
            "1": {"score": 0.0, "keywords": {}},
        }
        mock_repo.get_by_tender_id.return_value = mock_existing_score
        mock_repo.update_complaint_highlighted_keywords = MagicMock()
        mock_repo.flush = MagicMock()
        return mock_repo

    @pytest.fixture
    def mock_violation_score_repo(self):  # For new score scenario
        mock_repo = MagicMock(spec=ViolationScoreRepository)
        mock_repo.get_by_tender_id.return_value = None
        mock_repo.update_complaint_highlighted_keywords = MagicMock()
        mock_repo.create = MagicMock()
        return mock_repo

    @pytest.fixture
    def complaint_analysis_service(self, mock_violation_score_repo, mock_nlp_and_keywords):
        return ComplaintAnalysisService(mock_violation_score_repo)

    @pytest.fixture
    def complaint_analysis_service_existing_score(self, mock_violation_score_repo_existing_score,
                                                  mock_nlp_and_keywords):
        return ComplaintAnalysisService(mock_violation_score_repo_existing_score)

    def test_analyze_complaint_text_keyword_found(self, complaint_analysis_service):
        """Test when the keyword is found in the complaint text."""
        text = "Це дискримінаційний приклад."
        result = complaint_analysis_service.analyze_complaint_text(text)

        assert len(result) == 1
        highlight = result[0]
        assert highlight["keyword"] == "дискримінаційний"
        assert highlight["domains"] == ["0"]

        assert highlight["startPosition"] == 3
        assert highlight["length"] == len("дискримінаційний")

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
        result_score_obj = complaint_analysis_service_existing_score.update_violation_scores(tender_id, complaint)

        # Assert
        assert result_score_obj is not None
        expected_score_increase = math.log1p(1)

        assert result_score_obj.scores["0"]["score"] == pytest.approx(expected_score_increase)
        assert result_score_obj.scores["0"]["keywords"]["дискримінаційний"] == 1

        mock_violation_score_repo_existing_score.get_by_tender_id.assert_called_once_with(tender_id)

        expected_highlights = [{
            "keyword": "дискримінаційний", "domains": ["0"],
            "startPosition": 3, "length": len("дискримінаційний")
        }]
        mock_violation_score_repo_existing_score.update_complaint_highlighted_keywords.assert_called_once_with(
            complaint,
            expected_highlights
        )

        mock_violation_score_repo_existing_score.flush.assert_called_once()

    def test_update_violation_scores_new_score(self, complaint_analysis_service, mock_violation_score_repo):
        """Test creating violation scores when no existing score exists."""
        tender_id = "tender456"
        complaint = Complaint(id="complaint2", description="Це дискримінаційний приклад.")

        # Act
        result_score_obj = complaint_analysis_service.update_violation_scores(tender_id, complaint)

        # Assert
        assert result_score_obj is not None
        assert result_score_obj.tender_id == tender_id
        expected_score = math.log1p(1)
        assert result_score_obj.scores["0"]["score"] == pytest.approx(expected_score)
        assert result_score_obj.scores["0"]["keywords"]["дискримінаційний"] == 1

        mock_violation_score_repo.get_by_tender_id.assert_called_once_with(tender_id)

        expected_highlights = [{
            "keyword": "дискримінаційний", "domains": ["0"],
            "startPosition": 3, "length": len("дискримінаційний")
        }]
        mock_violation_score_repo.update_complaint_highlighted_keywords.assert_called_once_with(
            complaint,
            expected_highlights
        )


        mock_violation_score_repo.create.assert_called_once_with(result_score_obj)