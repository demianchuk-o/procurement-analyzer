import os
import logging
import re
from pathlib import Path

class CorpusWriter:
    """Writes cleaned text data to a series of text files in a specified directory."""

    def __init__(self, corpus_dir: str, max_lines_per_file: int = 1000, file_prefix: str = "corpus_"):
        """
        Initializes the CorpusWriter.

        :param corpus_dir: The directory where corpus files will be stored.
        :param max_lines_per_file: The maximum number of lines per text file.
        :param file_prefix: The prefix for the corpus filenames.
        """
        self.corpus_dir = Path(corpus_dir)
        self.max_lines_per_file = max_lines_per_file
        self.file_prefix = file_prefix
        self.logger = logging.getLogger(type(self).__name__)

        self.current_file_index = 0
        self.current_line_count = 0
        self.current_file_path = None

        try:
            self.corpus_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Corpus directory set to: '{self.corpus_dir}'")
        except OSError as e:
            self.logger.error(f"Failed to create corpus directory '{self.corpus_dir}': {e}", exc_info=True)
            raise

        self._initialize_state()
        self.logger.info(f"CorpusWriter initialized. Current state: File index {self.current_file_index}, "
                         f"Line count {self.current_line_count}, Path '{self.current_file_path}'")


    def _initialize_state(self):
        """Determines the starting file index and line count based on existing files."""
        last_file_index = -1
        file_pattern = re.compile(rf"^{re.escape(self.file_prefix)}(\d+)\.txt$")

        try:
            for filename in os.listdir(self.corpus_dir):
                match = file_pattern.match(filename)
                if match:
                    index = int(match.group(1))
                    if index > last_file_index:
                        last_file_index = index
        except OSError as e:
             self.logger.error(f"Error listing directory '{self.corpus_dir}' during initialization: {e}")


        self.current_file_index = last_file_index + 1

        if last_file_index >= 0:
            # check the last file for line count
            last_file_path = self._get_file_path(last_file_index)
            try:
                with open(last_file_path, 'r', encoding='utf-8') as f:
                    lines = sum(1 for _ in f)
                self.logger.info(f"Found existing file '{last_file_path}' with {lines} lines.")
                if lines < self.max_lines_per_file:
                    self.current_file_index = last_file_index
                    self.current_line_count = lines
                    self.logger.info(f"Resuming writing to '{last_file_path}'.")
                else:
                    self.current_line_count = 0
                    self.logger.info(f"Last file '{last_file_path}' is full. Starting new file.")

            except FileNotFoundError:
                 self.logger.warning(f"Last detected file index {last_file_index} but file '{last_file_path}' not found. Starting new file.")
                 self.current_line_count = 0
            except Exception as e:
                 self.logger.error(f"Error reading line count from '{last_file_path}': {e}. Starting new file.")
                 self.current_line_count = 0
        else:
            # if no existing files found, starting from index 0, line 0
            self.current_line_count = 0

        self.current_file_path = self._get_file_path(self.current_file_index)


    def _get_file_path(self, index: int) -> Path:
        """Generates the file path for a given index."""
        # corpus_0001 format
        filename = f"{self.file_prefix}{index:04d}.txt"
        return self.corpus_dir / filename

    def _rollover_file(self):
        """Moves to the next file index and resets the line count."""
        self.current_file_index += 1
        self.current_line_count = 0
        self.current_file_path = self._get_file_path(self.current_file_index)
        self.logger.info(f"Rolling over to new corpus file: '{self.current_file_path}'")

    def write(self, cleaned_text: str) -> None:
        """
        Writes a single line of cleaned text to the current corpus file.
        Handles file rollover when max_lines_per_file is reached.

        :param cleaned_text: The text string to write (should not contain newlines).
        """
        if not isinstance(cleaned_text, str) or not cleaned_text:
            self.logger.warning("Attempted to write invalid or empty text. Skipping.")
            return
        if '\n' in cleaned_text:
             self.logger.warning("Cleaned text contains newline characters. Writing as is, but this might indicate an issue.")


        try:
            if self.current_line_count >= self.max_lines_per_file:
                self._rollover_file()

            # directory might be deleted externally
            self.corpus_dir.mkdir(parents=True, exist_ok=True)

            with open(self.current_file_path, 'a', encoding='utf-8') as f:
                f.write(cleaned_text + "\n")

            self.current_line_count += 1
            self.logger.debug(f"Wrote line {self.current_line_count}/{self.max_lines_per_file} to '{self.current_file_path}'")

        except OSError as e:
            self.logger.error(f"Failed to write to corpus file '{self.current_file_path}': {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during write: {e}", exc_info=True)