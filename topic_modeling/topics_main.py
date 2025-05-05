import logging

from pathlib import Path

from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import normalize
from pandas import DataFrame
import pandas as pd

from topic_modeling.topic_utils import load_corpus, load_stopwords_from_url, display_topics, get_topics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus_texts"
N_TOPICS = 7 # number of topics from the graph
N_TOP_WORDS = 10
MAX_DF = 0.95
MIN_DF = 20

STOPWORDS_URL = "https://raw.githubusercontent.com/skupriienko/Ukrainian-Stopwords/refs/heads/master/stopwords_ua.txt"

if __name__ == "__main__":
    documents = load_corpus(CORPUS_DIR)
    if not documents:
        logging.error("No documents loaded. Exiting.")
        exit(1)

    try:
        ukrainian_stopwords = load_stopwords_from_url(STOPWORDS_URL)
        logging.info(f"Loaded {len(ukrainian_stopwords)} stop words.")
        ukrainian_stopwords += ["ст"]
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
        tokenizer= lambda doc: doc.split(),
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


    logging.info(f"Initializing NMF with {N_TOPICS} topics...")
    nmf_model = NMF(
        n_components=N_TOPICS,
        random_state=42,
        max_iter=500,
        init='nndsvda',
        l1_ratio=1,
        tol=1e-5,
        alpha_W=.0,
        alpha_H="same"
    )
    logging.info("Fitting NMF model...")
    nmf_model.fit(dtm)
    logging.info("NMF model fitting complete.")

    W = nmf_model.fit_transform(dtm)
    H = nmf_model.components_

    labels = W.argmax(axis=1)
    W_normalized = normalize(W)

    dbi = davies_bouldin_score(W_normalized, labels)
    logging.info(f"Davies-Bouldin Index: {dbi:.4f}")

    sil_core = silhouette_score(W_normalized, labels)
    logging.info(f"Silhouette Score: {sil_core:.4f}")

    logging.info("Displaying top words for each topic:")
    topics = get_topics(nmf_model, feature_names, N_TOP_WORDS)
    display_topics(topics)

    logging.info("Topic modeling complete.")

    corpus_topic_df = DataFrame.from_dict({
        "Document": range(len(documents)),
        "Dominant Topic": [topic + 1 for topic in labels],
        "Contribution, %": [max(doc_topics) * 100 for doc_topics in W_normalized],
        "Topic Desc": [", ".join([feature_names[i] for i in H[topic_idx].argsort()[:-N_TOP_WORDS - 1:-1]]) for topic_idx in labels]
    })
    corpus_topic_df.set_index("Document", inplace=True)

    pd.set_option('display.width', 1000)
    pd.set_option('display.max_columns', None)
    corpus_topic_df.sort_values(by="Contribution, %", ascending=False, inplace=True)
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 6), dpi=250)

    topic_counts = corpus_topic_df["Dominant Topic"].value_counts()
    plt.bar(topic_counts.index, topic_counts.values)
    plt.xlabel("Номер теми")
    plt.ylabel("Кількість документів по темі")
    plt.title("Розподіл документів по темах")
    plt.show()
    print(corpus_topic_df)
