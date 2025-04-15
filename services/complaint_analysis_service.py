import logging
from collections import Counter
from typing import List, Dict
import json

from celery import shared_task
from nltk.stem import SnowballStemmer
from nltk.tokenize import word_tokenize

stemmer = SnowballStemmer("russian")

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
                 keywords_path: str = '../util/keywords.json'):
        self.violation_score_repo = violation_score_repo
        self.logger = logging.getLogger(type(self).__name__)
        self.stemmer = stemmer
        self.stemmed_keywords = self._load_and_stem_keywords(keywords_path)

    def _load_and_stem_keywords(self, keywords_path: str) -> Dict:
        """Loads keywords from a JSON file and stems them."""
        keywords = self._load_keywords(keywords_path)
        stemmed_keywords = {}
        for domain, words in keywords.items():
            stemmed_keywords[domain] = list(set(self.stemmer.stem(word.lower()) for word in words))
        return stemmed_keywords

    def _load_keywords(self, keywords_path: str) -> Dict:
        """Loads keywords from a JSON file."""
        with open(keywords_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def analyze_complaint_text(self, complaint_text: str) -> List[Dict]:
        """Analyzes complaint text using stemming and returns highlighted keywords."""
        tokenized_complaint = word_tokenize(complaint_text.lower())
        stemmed_tokens = [self.stemmer.stem(token) for token in tokenized_complaint]
        highlighted = []
        for domain, keywords in self.stemmed_keywords.items():
            for keyword in keywords:
                if keyword in stemmed_tokens:
                    index = stemmed_tokens.index(keyword)
                    original_token = tokenized_complaint[index]
                    start = complaint_text.lower().find(original_token)
                    if start != -1:
                        highlighted.append({
                            "Keyword": original_token,
                            "Domain": domain,
                            "StartPosition": start,
                            "Length": len(original_token)
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
                most_frequent_domain_name = most_frequent_domain[0][0]
                if most_frequent_domain_name == "discriminatory_requirements":
                    scores["discriminatory_requirements_score"] += 1
                elif most_frequent_domain_name == "unjustified_high_price":
                    scores["unjustified_high_price_score"] += 1
                elif most_frequent_domain_name == "tender_documentation_issues":
                    scores["tender_documentation_issues_score"] += 1
                elif most_frequent_domain_name == "procedural_violations":
                    scores["procedural_violations_score"] += 1
                elif most_frequent_domain_name == "technical_specification_issues":
                    scores["technical_specification_issues_score"] += 1


        existing_score = self.violation_score_repo.get_by_tender_id(tender_id)
        if existing_score:
            existing_score.discriminatory_requirements_score = scores["discriminatory_requirements_score"]
            existing_score.unjustified_high_price_score = scores["unjustified_high_price_score"]
            existing_score.tender_documentation_issues_score = scores["tender_documentation_issues_score"]
            existing_score.procedural_violations_score = scores["procedural_violations_score"]
            existing_score.technical_specification_issues_score = scores["technical_specification_issues_score"]

            self.violation_score_repo.flush()
            self.violation_score_repo.commit()

            self.logger.info(f"Updated violation scores for tender {tender_id}")
            return existing_score
        else:
            new_score = ViolationScore(
                tender_id=tender_id,
                discriminatory_requirements_score=scores["discriminatory_requirements_score"],
                unjustified_high_price_score=scores["unjustified_high_price_score"],
                tender_documentation_issues_score=scores["tender_documentation_issues_score"],
                procedural_violations_score=scores["procedural_violations_score"],
                technical_specification_issues_score=scores["technical_specification_issues_score"]
            )
            self.violation_score_repo.create(new_score)

            self.logger.info(f"Created violation scores for tender {tender_id}")
            return new_score