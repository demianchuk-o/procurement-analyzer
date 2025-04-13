import logging
from collections import Counter

import spacy
from typing import List, Dict
import json

from celery import shared_task

from db import db
from models.complaints import Complaint
from models.violation_scores import ViolationScore
from repositories.tender_repository import TenderRepository
from repositories.violation_score_repository import ViolationScoreRepository

nlp = spacy.load("uk_core_news_md")

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
                 keywords_path: str = '../util/keywords.json'):
        self.violation_score_repo = violation_score_repo
        self.logger = logging.getLogger(type(self).__name__)
        self.violation_keywords = self._load_keywords(keywords_path)

    def _load_keywords(self, keywords_path: str) -> Dict:
        """Loads keywords from a JSON file."""
        with open(keywords_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def analyze_complaint_text(self, complaint_text: str) -> List[Dict]:
        """Analyzes complaint text and returns highlighted keywords."""
        doc = nlp(complaint_text)
        lemmatized_tokens = [token.lemma_.lower() for token in doc]
        highlighted = []
        for domain, keywords in self.violation_keywords.items():
            for keyword in keywords:
                if keyword.lower() in lemmatized_tokens:
                    start = complaint_text.lower().find(keyword.lower())
                    if start != -1:
                        highlighted.append({
                            "Keyword": keyword,
                            "Domain": domain,
                            "StartPosition": start,
                            "Length": len(keyword)
                        })
        return highlighted

    def update_violation_scores(self, tender_id: str, complaint: Complaint) -> ViolationScore:
        """Updates violation scores based on complaint analysis."""
        scores = {
            "discriminatory_requirements_score": 0,
            "unjustified_high_price_score": 0,
            "tender_documentation_issues_score": 0,
            "procedural_violations_score": 0,
            "technical_specification_issues_score": 0
        }

        if complaint.description:
            highlighted_keywords = self.analyze_complaint_text(complaint.description)
            complaint.highlighted_keywords = highlighted_keywords

            domain_counts = Counter(item["Domain"] for item in highlighted_keywords)
            most_frequent_domain = domain_counts.most_common(1)

            if most_frequent_domain:
                most_frequent_domain = most_frequent_domain[0][0]
                if most_frequent_domain == "discriminatory_requirements":
                    scores["discriminatory_requirements_score"] += 1
                elif most_frequent_domain == "unjustified_high_price":
                    scores["unjustified_high_price_score"] += 1
                elif most_frequent_domain == "tender_documentation_issues":
                    scores["tender_documentation_issues_score"] += 1
                elif most_frequent_domain == "procedural_violations":
                    scores["procedural_violations_score"] += 1
                elif most_frequent_domain == "technical_specification_issues":
                    scores["technical_specification_issues_score"] += 1


        existing_score = self.violation_score_repo.get_by_tender_id(tender_id)
        if existing_score:
            existing_score.discriminatory_requirements_score = scores["discriminatory_requirements_score"]
            existing_score.unjustified_high_price_score = scores["unjustified_high_price_score"]
            existing_score.tender_documentation_issues_score = scores["tender_documentation_issues_score"]
            existing_score.procedural_violations_score = scores["procedural_violations_score"]
            existing_score.technical_specification_issues_score = scores["technical_specification_issues_score"]
            updated_score = self.violation_score_repo.update(existing_score)
            self.logger.info(f"Updated violation scores for tender {tender_id}")
            return updated_score
        else:
            new_score = ViolationScore(
                tender_id=tender_id,
                discriminatory_requirements_score=scores["discriminatory_requirements_score"],
                unjustified_high_price_score=scores["unjustified_high_price_score"],
                tender_documentation_issues_score=scores["tender_documentation_issues_score"],
                procedural_violations_score=scores["procedural_violations_score"],
                technical_specification_issues_score=scores["technical_specification_issues_score"]
            )
            created_score = self.violation_score_repo.create(new_score)
            self.logger.info(f"Created violation scores for tender {tender_id}")
            return created_score