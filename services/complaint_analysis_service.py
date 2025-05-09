import json
import logging
import os
from collections import defaultdict
from typing import List, Dict

import spacy
from celery_app import app as celery_app
import math

from exceptions import NlpModelNotAvailableError, NlpResourcesNotAvailableError
from models import Complaint
from models import ViolationScore
from repositories.tender_repository import TenderRepository
from repositories.violation_score_repository import ViolationScoreRepository
from util.db_context_manager import session_scope


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def analyze_complaint_and_update_score(tender_id: str, complaint_id: str):
    """
    Asynchronous task to analyze a complaint and update the violation score.
    """
    logger = logging.getLogger(__name__)
    from app import app
    with app.app_context(), session_scope() as session:
        try:
                violation_score_repo = ViolationScoreRepository(session)
                tender_repo = TenderRepository(session)

                complaint_analysis_service = ComplaintAnalysisService(violation_score_repo)

                complaint = tender_repo.get_complaint_by_id(complaint_id)
                complaint_analysis_service.update_violation_scores(tender_id, complaint)
        except Exception as exc:
            logger.error(f"Error analyzing complaint {complaint_id} for tender {tender_id}: {exc}", exc_info=True)
            raise


class ComplaintAnalysisService:
    def __init__(self, violation_score_repo: ViolationScoreRepository):
        from signals import NLP_MODEL, LEMMATIZED_KEYWORDS

        self.logger = logging.getLogger(__name__)
        self.violation_score_repo = violation_score_repo
        self.nlp = NLP_MODEL
        self.lemmatized_keywords = LEMMATIZED_KEYWORDS

        if not self.nlp:
            self.logger.critical("CRITICAL: SpaCy model not available. ComplaintAnalysisService cannot function.")
            raise NlpModelNotAvailableError("SpaCy model (NLP_MODEL) is not loaded.")
        if not self.lemmatized_keywords:
            self.logger.critical(
                "CRITICAL: Lemmatized keywords not available. ComplaintAnalysisService functionality limited.")
            raise NlpResourcesNotAvailableError("Lemmatized keywords are not loaded.")


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
                                "keyword": token.lemma_,
                                "domain": domain,
                                "startPosition": start,
                                "length": len(token.text)
                            })
        return highlighted

    def update_violation_scores(self, tender_id: str, complaint: Complaint) -> ViolationScore:
        """Updates violation scores by adding new complaint scores to existing ones."""
        highlighted_keywords = self.analyze_complaint_text(complaint.description)
        aggregated = defaultdict(lambda: {"domains": set(), "startPosition": 0, "length": 0, "count": 0})
        for item in highlighted_keywords:
            lemma, domain, startPosition, length = item["keyword"], item["domain"], item["startPosition"], item["length"]
            aggregated[lemma]["domains"].add(domain)
            aggregated[lemma]["startPosition"] = startPosition
            aggregated[lemma]["length"] = length
            aggregated[lemma]["count"] += 1

        complaint_keywords = [
            {"keyword": k, "domains": list(v["domains"]), "startPosition": v["startPosition"], "length": v["length"]}
            for k, v in aggregated.items()
        ]
        self.violation_score_repo.update_complaint_highlighted_keywords(complaint, complaint_keywords)

        new_domain_data = {}
        for lemma, data in aggregated.items():
            weight = math.log1p(data["count"])
            for d in data["domains"]:
                dom = new_domain_data.setdefault(d, {"score": 0.0, "keywords": {}})
                dom["score"] += weight
                dom["keywords"][lemma] = dom["keywords"].get(lemma, 0) + data["count"]


        existing = self.violation_score_repo.get_by_tender_id(tender_id)
        if existing:
            merged = {}
            for domain, new in new_domain_data.items():
                prev = existing.scores.get(domain, {"score": 0.0, "keywords": {}})
                # sum scores
                total_score = prev["score"] + new["score"]
                # merge keyword counts
                kw_counts = defaultdict(int, prev.get("keywords", {}))
                for kw, cnt in new["keywords"].items():
                    kw_counts[kw] += cnt
                merged[domain] = {
                    "score": total_score,
                    "keywords": dict(kw_counts)
                }
            existing.scores = merged
            self.violation_score_repo.flush()
            self.violation_score_repo.commit()
            return existing


        created = ViolationScore(
            tender_id=tender_id,
            scores={d: {"score": v["score"], "keywords": v["keywords"]} for d, v in new_domain_data.items()}
        )
        self.violation_score_repo.create(created)
        return created