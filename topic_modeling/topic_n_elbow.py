import logging
from pathlib import Path

import numpy as np
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import normalize

from topic_modeling.topic_utils import load_corpus, load_stopwords_from_url

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus_texts"
N_TOPICS = 10
N_TOP_WORDS = 15
MAX_DF = 0.95
MIN_DF = 2

STOPWORDS_URL = "https://raw.githubusercontent.com/skupriienko/Ukrainian-Stopwords/refs/heads/master/stopwords_ua.txt"

if __name__ == "__main__":
    documents = load_corpus(CORPUS_DIR)
    if not documents:
        logging.error("No documents loaded. Exiting.")
        exit(1)

    try:
        ukrainian_stopwords = load_stopwords_from_url(STOPWORDS_URL)
        logging.info(f"Loaded {len(ukrainian_stopwords)} stop words.")
    except Exception as e:
        logging.warning(f"Could not load NLTK stopwords, proceeding without them: {e}")
        ukrainian_stopwords = None


    logging.info("Initializing CountVectorizer...")
    vectorizer = CountVectorizer(
        max_df=MAX_DF,
        min_df=MIN_DF,
        stop_words=ukrainian_stopwords,
        ngram_range=(1, 1),
        token_pattern=None,
        tokenizer=lambda doc: doc.split(),
        preprocessor=lambda doc: doc
    )
    logging.info("Fitting CountVectorizer and transforming data...")
    try:
        dtm = vectorizer.fit_transform(documents)
        feature_names = vectorizer.get_feature_names_out()
        logging.info(f"Created Document-Term Matrix with shape: {dtm.shape}")
        logging.info(f"Vocabulary size: {len(feature_names)}")
    except ValueError as e:
        logging.error(f"Error during vectorization: {e}. Check preprocessing/stopwords.")
        exit(1)

    dbi_scores = []
    silhouette_scores = []

    for n in range(2, 21):
        nmf = NMF(
            n_components=n,
            random_state=42,
            max_iter=10000,
            init='nndsvda',
            l1_ratio=1,
            tol=1e-5,
            alpha_W=.0,
            alpha_H="same"
        )
        W = nmf.fit_transform(dtm)
        H = nmf.components_

        labels = W.argmax(axis=1)
        W_norm = normalize(W)
        try:
            dbi = davies_bouldin_score(W_norm, labels)
            sil = silhouette_score(W_norm, labels)
        except Exception:
            dbi = np.nan
            sil = np.nan

        dbi_scores.append(dbi)
        silhouette_scores.append(sil)

    import matplotlib.pyplot as plt

    x = list(range(2, 21))

    plt.figure(figsize=(10, 6), dpi=250)
    plt.plot(x, dbi_scores, label="Davies–Bouldin Index", marker='s')
    plt.plot(x, silhouette_scores, label="Silhouette Score", marker='^')
    plt.xlabel("Кількість тем")
    plt.ylabel("Значення метрик кластеризації")
    plt.title("Davies–Bouldin та Silhouette для різної кількості тем")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    a = 0.5
    compromise_scores = [a * sil - (1 - a) * dbi for sil, dbi in zip(silhouette_scores, dbi_scores)]

    plt.figure(figsize=(10, 6), dpi=250)
    plt.plot(x, compromise_scores, label=f"Compromise Criterion (a={a})", marker='x')
    plt.xlabel("Кількість тем")
    plt.ylabel("Значення критерію")
    plt.title("Компромісний критерій для різної кількості тем")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()