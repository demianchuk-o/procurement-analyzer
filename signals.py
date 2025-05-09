from celery.signals import worker_process_init
import spacy
import os
import json
import logging

NLP_MODEL = None
LEMMATIZED_KEYWORDS = None

@worker_process_init.connect
def init_nlp_model(**kwargs):
    global NLP_MODEL, LEMMATIZED_KEYWORDS
    logger = logging.getLogger("celery.worker.nlp_loader")
    if NLP_MODEL is None:
        try:
            logger.info("Loading SpaCy model and keywords for worker process...")
            NLP_MODEL = spacy.load("uk_core_news_sm", disable=["parser", "ner"])

            project_root = os.path.dirname(os.path.abspath(__file__)) # signals.py is in the root directory
            keywords_path = os.path.join(project_root, 'keywords.json') # keywords are in root too

            if not os.path.exists(keywords_path):
                logger.error(f"Keywords file not found at: {keywords_path}")
                LEMMATIZED_KEYWORDS = {}
                return

            with open(keywords_path, 'r', encoding='utf-8') as file:
                keywords_data = json.load(file)

            LEMMATIZED_KEYWORDS = {}
            for domain, words in keywords_data.items():
                LEMMATIZED_KEYWORDS[domain] = [NLP_MODEL(word)[0].lemma_ for word in words]

            logger.info("SpaCy model and keywords loaded successfully for worker process.")
        except Exception as e:
            logger.critical(
                f"FAILED to load SpaCy model or keywords on worker_process_init: {e}. NLP_MODEL will be None.",
                exc_info=True)
            NLP_MODEL = None
            LEMMATIZED_KEYWORDS = None