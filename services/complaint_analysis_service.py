import json
import logging
import os
from collections import Counter
from typing import List, Dict

import spacy
from celery import shared_task

from db import db
from models import Complaint
from models import ViolationScore
from repositories.tender_repository import TenderRepository
from repositories.violation_score_repository import ViolationScoreRepository


@shared_task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def analyze_complaint_and_update_score(tender_id: str, complaint_id: str):
    """
    Asynchronous task to analyze a complaint and update the violation score.
    """
    logger = logging.getLogger(__name__)
    try:
        violation_score_repo = ViolationScoreRepository(db.session)
        tender_repo = TenderRepository(db.session)

        complaint_analysis_service = ComplaintAnalysisService(violation_score_repo)

        complaint = tender_repo.get_complaint_by_id(complaint_id)
        complaint_analysis_service.update_violation_scores(tender_id, complaint)
    except Exception as exc:
        logger.error(f"Error analyzing complaint {complaint_id} for tender {tender_id}: {exc}", exc_info=True)
        raise
    finally:
        db.session.close()


class ComplaintAnalysisService:
    def __init__(self, violation_score_repo: ViolationScoreRepository,
                 keywords_path: str = '../keywords.json',
                 spacy_model: str = "uk_core_news_sm"):
        self.violation_score_repo = violation_score_repo
        self.logger = logging.getLogger(type(self).__name__)
        self.nlp = spacy.load(spacy_model, disable=["parser", "ner"])
        script_dir = os.path.dirname(os.path.abspath(__file__))
        full_keywords_path = os.path.join(script_dir, keywords_path)
        self.keywords = self._load_keywords(full_keywords_path)
        self.lemmatized_keywords = self._lemmatize_keywords(self.keywords)

    def _load_keywords(self, keywords_path: str) -> Dict:
        """Loads keywords from a JSON file."""
        with open(keywords_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def _lemmatize_keywords(self, keywords: Dict) -> Dict[str, List[str]]:
        """Lemmatizes keywords using spaCy."""
        lemmatized_keywords = {}
        for domain, words in keywords.items():
            lemmatized_keywords[domain] = [self.nlp(word)[0].lemma_ for word in words]
        return lemmatized_keywords

    def analyze_complaint_text(self, complaint_text: str) -> List[Dict]:
        """Analyzes complaint text using spaCy lemmatization and returns highlighted keywords."""
        doc = self.nlp(complaint_text.lower())
        highlighted = []
        for domain, keywords in self.lemmatized_keywords.items():
            for keyword in keywords:
                for token in doc:
                    if token.lemma_ == keyword:
                        start = complaint_text.lower().find(token.text)
                        if start != -1:
                            highlighted.append({
                                "Keyword": token.text,
                                "Domain": domain,
                                "StartPosition": start,
                                "Length": len(token.text)
                            })
        return highlighted

    def update_violation_scores(self, tender_id: str, complaint: Complaint) -> ViolationScore:
        """Updates violation scores based on complaint analysis."""
        highlighted_keywords = []
        if complaint.description:
            highlighted_keywords = self.analyze_complaint_text(complaint.description)
            complaint.highlighted_keywords = highlighted_keywords

        domain_counts = Counter(item["Domain"] for item in highlighted_keywords)
        scores = {domain: count for domain, count in domain_counts.items()}

        existing_score = self.violation_score_repo.get_by_tender_id(tender_id)
        if existing_score:
            existing_score.scores = scores
            self.violation_score_repo.flush()
            self.violation_score_repo.commit()

            self.logger.info(f"Updated violation scores for tender {tender_id}")
            return existing_score
        else:
            new_score = ViolationScore(tender_id=tender_id, scores=scores)
            self.violation_score_repo.create(new_score)

            self.logger.info(f"Created violation scores for tender {tender_id}")
            return new_score