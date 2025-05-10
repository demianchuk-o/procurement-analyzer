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
        if not complaint_text:
            return []
        doc = self.nlp(complaint_text.lower())
        
        # key: ((start_char_offset, length_of_token)
        # value: {"lemma": "...", "domains": set()}
        textual_occurrences = {}
        
        for token in doc:
            token_lemma_lower = token.lemma_.lower()
            for domain, domain_keyword_lemmas in self.lemmatized_keywords.items():
                if token_lemma_lower in domain_keyword_lemmas:
                    key = (token.idx, len(token.text))
                    if key not in textual_occurrences:
                        textual_occurrences[key] = {
                            "lemma": token_lemma_lower,
                            "domains": set()
                        }
                    textual_occurrences[key]["domains"].add(domain)
        
        highlights = []
        for (start, length), data in textual_occurrences.items():
            highlights.append({
                "keyword": data["lemma"],
                "domains": list(data["domains"]),
                "startPosition": start,
                "length": length
            })
        return highlights

    def update_violation_scores(self, tender_id: str, complaint: Complaint) -> ViolationScore:
        """Updates violation scores by adding new complaint scores to existing ones."""
        
        complaint_specific_highlights = self.analyze_complaint_text(complaint.description)
        
        self.violation_score_repo.update_complaint_highlighted_keywords(complaint, complaint_specific_highlights)


        lemma_counts_per_domain = defaultdict(lambda: defaultdict(int))
        
        for highlight_item in complaint_specific_highlights:
            lemma = highlight_item["keyword"]
            for domain_from_item in highlight_item["domains"]:
                lemma_counts_per_domain[domain_from_item][lemma] += 1
        
        new_domain_data = {} # {"score": float, "keywords": Dict[strLemma, intCount]} per domain
        for domain_name, counts_for_this_domain in lemma_counts_per_domain.items():
            current_domain_score_contribution = 0.0
            current_domain_keywords_map = {} # {"keywords": {"lemma1": count, "lemma2": count}}
            
            for lemma, count in counts_for_this_domain.items():
                weight = math.log1p(count)
                current_domain_score_contribution += weight
                current_domain_keywords_map[lemma] = count
            
            if current_domain_score_contribution > 0:
                 new_domain_data[domain_name] = {
                     "score": current_domain_score_contribution,
                     "keywords": current_domain_keywords_map
                 }


        existing = self.violation_score_repo.get_by_tender_id(tender_id)
        if existing:
            merged_scores = existing.scores.copy()
            for domain, new_data in new_domain_data.items():
                prev_domain_data = merged_scores.get(domain, {"score": 0.0, "keywords": {}})
                
                total_score = prev_domain_data["score"] + new_data["score"]
                

                kw_counts_for_domain = defaultdict(int, prev_domain_data.get("keywords", {}))
                for kw, cnt in new_data["keywords"].items():
                    kw_counts_for_domain[kw] += cnt
                
                merged_scores[domain] = {
                    "score": total_score,
                    "keywords": dict(kw_counts_for_domain)
                }
            
            for domain, prev_data in existing.scores.items():
                if domain not in merged_scores:
                    merged_scores[domain] = prev_data

            existing.scores = merged_scores
            self.violation_score_repo.flush()
            return existing


        created = ViolationScore(
            tender_id=tender_id,
            scores=new_domain_data
        )
        self.violation_score_repo.create(created)
        return created