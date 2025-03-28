import logging
import time
from typing import Optional, Dict, Any

import requests
from urllib.parse import urljoin


class LegacyProzorroClient:
    # Publicly available API endpoint for detailed data
    BASE_URL = 'https://public.api.openprocurement.org/api/2.5/tenders/'

    def __init__(self, retry_count: int = 3, retry_delay: int = 1,
                 timeout: int = 15) -> None:  # Increased timeout slightly
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.logger = logging.getLogger(type(self).__name__)

    def fetch_tender_details(self, tender_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Fetches detailed data for a specific tender using its 32-char UUID.
        :param tender_uuid: The 32-character UUID ('id') of the tender.
        :return: Dict containing the 'data' part of the JSON response, or None on failure.
        """
        if not tender_uuid:
            self.logger.error("tender_uuid cannot be empty.")
            return None

        url = urljoin(self.BASE_URL, tender_uuid)  # Simple join gives BASE_URL/tender_uuid
        self.logger.info(f"Fetching legacy tender details for UUID {tender_uuid}")

        for attempt in range(1, self.retry_count + 1):
            try:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()

                response_json = response.json()

                data = response_json.get("data")
                if data:
                    self.logger.info(f"Successfully fetched legacy details for UUID {tender_uuid}")
                    return data
                else:
                    self.logger.error(
                        f"No 'data' key found in response for UUID {tender_uuid} on attempt {attempt}/{self.retry_count}")
                    return None

            except requests.exceptions.RequestException as e:
                self.logger.error(
                    f"Request error fetching legacy details for UUID {tender_uuid} on attempt {attempt}/{self.retry_count}: {e}")
            except Exception as e:
                self.logger.error(
                    f"Error processing legacy details response for UUID {tender_uuid} on attempt {attempt}/{self.retry_count}: {e}")

            if attempt < self.retry_count:
                time.sleep(self.retry_delay)

        self.logger.error(f"Max retries exceeded or fatal error fetching legacy details for UUID {tender_uuid}")
        return None