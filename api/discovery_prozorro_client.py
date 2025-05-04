import logging
import time
from typing import Optional, Dict, List, Any
import requests
from urllib.parse import urljoin

from schemas.discovery_schema import SearchPageSchema, TenderBridgeInfoSchema


class DiscoveryProzorroClient:
    BASE_URL = 'https://prozorro.gov.ua/api/'
    SEARCH_ENDPOINT = 'search/tenders/'
    TENDER_ENDPOINT = 'tenders/'
    COMPLAINTS_SUBPATH = 'complaints/'  # Added for the new method

    def __init__(self, retry_count: int = 3, retry_delay: int = 1, timeout: int = 10) -> None:
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.logger = logging.getLogger(type(self).__name__)
        self.search_page_schema = SearchPageSchema()
        self.bridge_info_schema = TenderBridgeInfoSchema()

    def _make_request(self, method: str, url: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
        """Internal helper to make requests with retries."""
        for attempt in range(1, self.retry_count + 1):
            try:
                response = requests.request(method, url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error on attempt {attempt}/{self.retry_count} for URL {url}: {e}")
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay * attempt) # Exponential backoff can be better
            except Exception as e:
                 self.logger.error(f"Unexpected error on attempt {attempt}/{self.retry_count} for URL {url}: {e}")
                 break

        self.logger.error(f"Max retries exceeded or fatal error for URL {url}")
        return None

    def fetch_search_page_tender_ids(self, page: int = 0,
                                     query_params: Optional[Dict[str, Any]] = None) -> Optional[List[str]]:
        """
        Fetches a specific page from the /search/tenders/ endpoint and returns only tenderIDs (OCIDs).
        :param page: The page number to fetch (0-based).
        :param query_params: Optional query parameters to filter the search.
        :return: List of tenderIDs (OCIDs) or None if an error occurs.
        """
        if page < 0:
            self.logger.error("Page number cannot be negative.")
            return None

        search_url = urljoin(self.BASE_URL, self.SEARCH_ENDPOINT)

        params = query_params.copy() if query_params else {}
        params["page"] = page if page > 0 else None
        self.logger.info(f"Fetching search page {page} with params: {params}")

        response = self._make_request("POST", search_url, params=params)

        if response:
            try:
                data = response.json()

                validated_data = self.search_page_schema.load(data)
                tender_ids = [tender_id for tender_id in validated_data.get('data', [])]
                self.logger.info(f"Successfully fetched {len(tender_ids)} tenderIDs from page {page}")
                return tender_ids
            except Exception as e:
                self.logger.error(f"Error processing/validating search page {page} response: {e}")

        return None

    def fetch_tender_bridge_info(self, tender_id_ocid: str) -> Optional[Dict[str, Any]]:
        """
        Fetches bridging information (UUID, OCID, generalClassifier, dateModified)
        for a specific tender using its OCID from the new API's /tenders/{ocid} endpoint.
        :param tender_id_ocid: The OCID (tenderID) of the tender.
        :return: Dict with bridge info or None if an error occurs.
        """
        if not tender_id_ocid:
            self.logger.error("tender_id_ocid cannot be empty.")
            return None

        tender_url = urljoin(self.BASE_URL, urljoin(self.TENDER_ENDPOINT, f"{tender_id_ocid}/"))
        self.logger.info(f"Fetching bridge info for tender OCID {tender_id_ocid}")

        response = self._make_request(tender_url)

        if response:
            try:
                data = response.json()
                validated_data = self.bridge_info_schema.load(data)
                self.logger.info(f"Successfully fetched bridge info for tender OCID {tender_id_ocid}")
                return validated_data
            except Exception as e:
                self.logger.error(f"Error processing/validating bridge info for OCID {tender_id_ocid}: {e}")

        return None
