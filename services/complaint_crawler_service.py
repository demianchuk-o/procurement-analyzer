import logging
import time

from api.discovery_prozorro_client import DiscoveryProzorroClient
from api.legacy_prozorro_client import LegacyProzorroClient
from services.text_processing_service import TextProcessingService


class ComplaintCrawlerService:
    def __init__(self, text_processing_service: TextProcessingService) -> None:
        self.discovery_client = DiscoveryProzorroClient()
        self.legacy_client = LegacyProzorroClient()

        self.text_processor = text_processing_service
        self.logger = logging.getLogger(type(self).__name__)


    def gather_complaint_claim_texts(self, max_texts: int = 1000, start_page: int = 0) -> int:
        """
                Crawls tenders, fetches legacy details, extracts complaint/claim texts, processes them and stores in a corpus.
                :param max_texts: The target number of complaint/claim texts to collect.
                :param start_page: The search page to start crawling from.
                :return: A count of complaint/claim texts processed.
                """
        self.logger.info(f"Starting complaint/claim text gathering. Target: {max_texts} unique texts.")

        query_params = {
            "proc_type[0]": "aboveThresholdUA",
            "proc_type[1]": "aboveThresholdEU",
            "proc_type[2]": "competitiveOrdering",
            "sort_by": "value.amount",
            "order": "desc",
        }

        seen_raw_texts = set()
        processed_texts_count = 0
        current_page = start_page

        while processed_texts_count < max_texts:
            self.logger.info(f"Fetching tender OCIDs from search page {current_page} with expensive tender parameters.")
            tender_ocids = self.discovery_client.fetch_search_page_tender_ids(
                page=current_page,
                query_params=query_params
            )

            if tender_ocids is None:
                self.logger.error(f"Failed to fetch tender OCIDs from page {current_page}. Stopping gathering.")
                break
            if not tender_ocids:
                self.logger.info(f"No more tender OCIDs found on page {current_page}. Stopping gathering.")
                break

            self.logger.info(f"Found {len(tender_ocids)} tender OCIDs on page {current_page}.")

            for ocid in tender_ocids:
                if processed_texts_count >= max_texts:
                    break


                self.logger.debug(f"Fetching bridge info for OCID: {ocid}")
                bridge_info = self.discovery_client.fetch_tender_bridge_info(ocid)
                if not bridge_info:
                    self.logger.warning(f"Could not fetch bridge info for OCID {ocid}, skipping.")
                    continue

                tender_uuid = bridge_info.get('id')
                if not tender_uuid:
                    self.logger.warning(f"Missing UUID in bridge info for OCID {ocid}, skipping.")
                    continue

                tender_details = self.legacy_client.fetch_tender_details(tender_uuid)
                if not tender_details:
                    self.logger.warning(f"Could not fetch legacy details for UUID {tender_uuid}, skipping.")
                    continue

                complaint_claim_texts = tender_details.get("complaints", [])
                if not complaint_claim_texts:
                    self.logger.warning(f"No complaints found in legacy details for UUID {tender_uuid}, skipping.")
                    continue

                for complaint in complaint_claim_texts:
                    if processed_texts_count >= max_texts:
                        seen_raw_texts.clear()
                        break

                    title = complaint.get("title")
                    description = complaint.get("description")

                    complaint_title_desc = f"{title} {description}"
                    if not complaint_title_desc in seen_raw_texts:
                        seen_raw_texts.add(complaint_title_desc)
                        processed_texts_count += 1
                        self.logger.info(f"Collected tender-unique complaint/claim text: {title[:50]}...")

                        # process the title and description
                        success = self.text_processor.process_and_store(complaint_title_desc)
                        if not success:
                            self.logger.warning(f"Failed to process and store text.")
                        else:
                            self.logger.info(f"Successfully processed and stored text.")

                        if processed_texts_count >= max_texts:
                            self.logger.info(f"Reached target of {max_texts} texts.")
                            seen_raw_texts.clear()
                            break

                seen_raw_texts.clear()

            if processed_texts_count >= max_texts:
                break

            current_page += 1

            time.sleep(0.5)

        self.logger.info(
            f"Complaint/claim text gathering finished. Found and processed {processed_texts_count} texts.")
        return processed_texts_count
