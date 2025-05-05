import logging
import re
from pathlib import Path
from typing import Optional, List

import numpy as np
import requests

from sklearn.decomposition import NMF


def load_corpus(corpus_dir: Path) -> list[str]:
    """Loads all documents from .txt files in the corpus directory."""
    texts = []
    if not corpus_dir.is_dir():
        logging.error(f"Corpus directory not found: {corpus_dir}")
        return texts
    for file_path in corpus_dir.glob("*.txt"):
        logging.info(f"Loading data from: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                texts.extend(line.strip() for line in f if line.strip())
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
    logging.info(f"Loaded {len(texts)} documents.")
    return texts

def preprocess_text(text: str) -> str:
    """Basic preprocessing: lowercase, remove non-alphanumeric (keeping Cyrillic)."""
    text = text.lower()
    # Remove punctuation and numbers, keep spaces and Cyrillic/basic Latin letters
    text = re.sub(r'[^а-яіїєґa-z\s]', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def load_stopwords_from_url(url: str) -> Optional[List[str]]:
    """Downloads stopwords from a URL (one word per line)."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        stopwords_list = [line for line in response.text.splitlines()]
        logging.info(f"Successfully loaded {len(stopwords_list)} stopwords from {url}")
        return stopwords_list
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download stopwords from {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An error occurred processing stopwords from {url}: {e}")
        return None

def display_topics(model: NMF, feature_names: list[str], n_top_words: int):
    """Prints the top words for each topic found by the NMF model."""
    #for topic_idx, topic in enumerate(model.components_):
    #    top_features_indices = topic.argsort()[:-n_top_words - 1:-1]
    #    top_features = [feature_names[i] for i in top_features_indices]
    #    print(f"Topic #{topic_idx}:")
    #    print(" ".join(top_features))

    topic_terms = model.components_
    vocabulary = np.array(feature_names)
    topic_key_term_idxs = np.argsort(-np.absolute(topic_terms), axis=1)[:, :n_top_words]
    topic_keyterms = vocabulary[topic_key_term_idxs]
    topics = [", ".join(topic) for topic in topic_keyterms]
    for i, topic in enumerate(topics):
        logging.info(f"Topic {i}: {topic}")