import logging
from pathlib import Path
from services.text_cleaner import TextCleaner
from services.corpus_writer import CorpusWriter

class TextProcessingService:
    """
    Orchestrates text cleaning and writing to a corpus.
    """

    def __init__(self, corpus_dir: str, max_lines_per_file: int = 1000, file_prefix: str = "corpus_"):
        """
        Initializes the service with a TextCleaner and CorpusWriter.

        :param corpus_dir: The directory for storing corpus files.
        :param max_lines_per_file: Max lines per corpus file for the writer.
        :param file_prefix: Prefix for corpus filenames.
        """
        self.logger = logging.getLogger(type(self).__name__)
        self.logger.info("Initializing TextProcessingService...")

        try:
            self.cleaner = TextCleaner()
            self.writer = CorpusWriter(str(Path(corpus_dir)), max_lines_per_file, file_prefix)
            self.logger.info("TextProcessingService initialized successfully.")
        except Exception as e:
            self.logger.exception(f"Failed to initialize TextProcessingService: {e}")

            raise

    def process_and_store(self, text: str) -> bool:
        """
        Cleans the input text and writes it to the corpus if it's not empty after cleaning.

        :param text: The raw text string to process (e.g., concatenated title and description).
        :return: True if the text was successfully processed and written (or skipped because it was empty after cleaning), False otherwise.
        """
        self.logger.debug(f"Processing text: '{text[:100]}...'")
        if not isinstance(text, str):
            self.logger.warning(f"Input must be a string, got {type(text)}. Skipping.")
            return False

        try:
            cleaned_text = self.cleaner.clean(text)

            if cleaned_text:
                self.logger.debug(f"Cleaned text: '{cleaned_text[:100]}...'. Writing to corpus.")
                self.writer.write(cleaned_text)
                return True
            else:
                self.logger.debug("Text became empty after cleaning. Skipping write.")
                return True
        except Exception as e:
            self.logger.error(f"Error during processing or storing text: {e}", exc_info=True)
            return False
