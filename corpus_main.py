import logging
from pathlib import Path

from services.complaint_crawler_service import ComplaintCrawlerService
from services.text_processing_service import TextProcessingService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Set up the corpus directory on the top level
corpus_dir = Path("./corpus_texts")
corpus_dir_str = str(corpus_dir.resolve())

number_of_texts = 5000

try:
    text_processor = TextProcessingService(corpus_dir=corpus_dir_str, max_lines_per_file=number_of_texts)
    logging.info(f"TextProcessingService initialized with corpus directory: {corpus_dir_str}")
except Exception as e:
    logging.exception("Failed to initialize TextProcessingService. Exiting.")
    exit(1)


crawler = ComplaintCrawlerService(
    text_processing_service=text_processor
)
logging.info("CrawlerService initialized.")


logging.info("Starting complaint/claim text gathering...")
try:
    processed_count = crawler.gather_complaint_claim_texts(max_texts=number_of_texts)
    logging.info(f"Finished gathering. Processed {processed_count} texts.")
except Exception as e:
    logging.exception("An error occurred during text gathering.")