import logging
import time
from typing import Optional, Dict, List, Any

import requests

from schemas.tenders_page_schema import TendersPageSchema

class ProzorroClient:
    # Publicly available API endpoint
    BASE_URL = 'https://public.api.openprocurement.org/api/2.5/tenders'

    def __init__(self, retry_count: int = 3, retry_delay: int = 1, timeout: int = 5) -> None:
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.logger = logging.getLogger(type(self).__name__)

    def fetch_tenders_page(self, offset: Optional[str], limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        Fetches a page of tenders from the API
        :param offset: string with the offset to fetch
        :param limit: number of tenders to fetch
        :return dict: JSON response from the API
        """

        params = { "limit": limit }
        if offset:
            params["offset"] = offset

        self.logger.info("Fetching tenders page with params: %", params)

        for attempt in range(1, self.retry_count + 1):
            try:
                response = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
                if response.status_code == 200:
                    page_schema = TendersPageSchema()
                    return page_schema.load(response.json())
                else:
                    self.logger.error(f"Status code {response.status_code} on attempt {attempt}/{self.retry_count}")
            except Exception as e:
                self.logger.error(f"Request error on attempt {attempt}/{self.retry_count}: {e}")

            if attempt < self.retry_count:
                time.sleep(self.retry_delay)

        self.logger.error("Max retries exceeded, returning None")
        return None

    def fetch_tender_details(self, tender_id: str) -> dict:
        """
        Fetches details of a specific tender
        :param tender_id:
        :return dict: JSON response from the API
        """

        url = f"{self.BASE_URL}/{tender_id}"
        self.logger.info(f"Fetching tender details for {tender_id}")

        for attempt in range(1, self.retry_count + 1):
            try:
                response = requests.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    response_json = response.json()
                    data = response_json.get("data", {})
                    return data
                else:
                    self.logger.error(f"Status code {response.status_code} for tender {tender_id} on attempt {attempt}/{self.retry_count}")
            except Exception as e:
                self.logger.error(f"Error fetching tender details for {tender_id} on attempt {attempt}/{self.retry_count}: {e}")

            if attempt < self.retry_count:
                time.sleep(self.retry_delay)

        return {}

    def fetch_all_tenders(self, start_offset: Optional[str] = None, limit: int = 100,
                          sleep_between_pages: int = 1) -> List[Dict[str, Any]]:
        """
        Fetches all tenders from the API by iterating over pages
        :param start_offset: offset to start fetching from
        :param limit: number of tenders to fetch per page
        :param sleep_between_pages: time to sleep between pages
        :return list: list of tenders
        """

        all_tenders = []
        offset = start_offset or "1741945278.273.1.3219c9397a4686aba9037be436bb0dc2"

        while True:
            page_data = self.fetch_tenders_page(offset=offset, limit=limit)
            if not page_data:
                self.logger.error("Failed to fetch a page, breaking")
                break

            tenders = page_data.get("data", [])
            if not tenders:
                self.logger.info("No more tenders found, breaking")
                break

            all_tenders.extend(tenders)
            self.logger.info(f"Fetched {len(tenders)} tenders, total {len(all_tenders)}")

            next_page = page_data.get("next_page", {})
            if next_page and next_page.get("offset"):
                offset = next_page.get("offset")
                self.logger.info(f"Next page offset: {offset}")
                time.sleep(sleep_between_pages)
            else:
                self.logger.info("No more pages, breaking")
                break

        return all_tenders