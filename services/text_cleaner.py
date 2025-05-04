import re
import logging

class TextCleaner:
    """Cleans text by lowercasing, removing numbers, filtering for Ukrainian words,
    removing punctuation, and normalizing whitespace."""

    def __init__(self):

        self._num_pattern = re.compile(r'\d+')
        self._punct_pattern = re.compile(r'[^\w\sа-яіїєґ]')
        self._space_pattern = re.compile(r'\s+')

        self._ukr_char_pattern = re.compile(r'[а-яіїєґ]')
        self.logger = logging.getLogger(type(self).__name__)
        self.logger.info("TextCleaner initialized.")

    def clean(self, text: str) -> str:
        """
        Applies the cleaning pipeline to the input text.
        :param text: The raw text string (e.g., concatenated title and description).
        :return: The cleaned text string containing primarily Ukrainian words.
        """
        if not isinstance(text, str):
             self.logger.warning(f"Input is not a string: {type(text)}. Returning empty string.")
             return ""
        if not text:
            return ""

        # lowercase
        cleaned_text = text.lower()
        self.logger.debug(f"Lowercased: '{cleaned_text[:100]}...'")

        # remove numbers
        cleaned_text = self._num_pattern.sub('', cleaned_text)
        self.logger.debug(f"Numbers removed: '{cleaned_text[:100]}...'")

        # normalize whitespace
        cleaned_text = self._space_pattern.sub(' ', cleaned_text).strip()
        self.logger.debug(f"Whitespace normalized (1): '{cleaned_text[:100]}...'")

        # 4. Split into words
        words = cleaned_text.split()

        # keep words only containing Ukrainian characters
        ukrainian_words = [word for word in words if self._ukr_char_pattern.search(word)]
        self.logger.debug(f"Filtered Ukrainian words count: {len(ukrainian_words)}")

        # join the kept words
        cleaned_text = ' '.join(ukrainian_words)
        self.logger.debug(f"Joined Ukrainian words: '{cleaned_text[:100]}...'")

        # remove anything not alphanumeric, whitespace, or Ukrainian letters
        cleaned_text = self._punct_pattern.sub('', cleaned_text)
        self.logger.debug(f"Punctuation removed: '{cleaned_text[:100]}...'")

        # normalize whitespace again
        cleaned_text = self._space_pattern.sub(' ', cleaned_text).strip()
        self.logger.debug(f"Whitespace normalized (2): '{cleaned_text[:100]}...'")

        if not cleaned_text:
             self.logger.debug("Text became empty after cleaning.")

        return cleaned_text