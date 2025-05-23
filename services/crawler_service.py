import logging

from datetime import timezone
from typing import Optional

from api.discovery_prozorro_client import DiscoveryProzorroClient
from services.data_processor import process_tender_data_task
from repositories.tender_repository import TenderRepository

finished_tenders_statuses = ["complete", "cancelled", "unsuccessful", "active.awarded", "draft.unsuccessful"]

class CrawlerService:
    def __init__(self, tender_repo: TenderRepository) -> None:
        self.discovery_client = DiscoveryProzorroClient()
        self.tender_repo = tender_repo
        self.logger = logging.getLogger(type(self).__name__)

    def sync_single_tender(self, tender_ocid: str, high_priority: bool = False) -> None:
        """
        Syncs a single tender using its OCID. Fetches data from both APIs if dateModified indicates a change.
        Manages DB transaction.
        """
        self.logger.info(f"Syncing single tender OCID {tender_ocid}")

        bridge_info = self.discovery_client.fetch_tender_bridge_info(tender_ocid)
        if not bridge_info:
            self.logger.warning(f"Could not fetch bridge info for tender OCID {tender_ocid}")
            return

        tender_uuid = bridge_info.get('id')
        date_modified_from_bridge = bridge_info.get('dateModified')
        classifier_data = bridge_info.get('generalClassifier')

        if not tender_uuid or not date_modified_from_bridge:
            self.logger.error(f"Missing UUID or dateModified in bridge info for OCID {tender_ocid}")
            return

        date_modified_utc = date_modified_from_bridge.astimezone(timezone.utc)

        try:
            existing_tender = self.tender_repo.get_short_by_uuid(tender_uuid)

            if (existing_tender is not None and existing_tender["date_modified"]
                    and existing_tender["date_modified"].astimezone(timezone.utc) >= date_modified_utc):
                self.logger.debug(
                    f"Tender UUID {tender_uuid} (OCID {tender_ocid}) is up to date. No sync needed.")
                return


            process_tender_data_task.apply_async(
                args=(tender_uuid, tender_ocid, date_modified_utc, classifier_data),
                queue='default',
                priority=5 if high_priority else 0
            )

            self.logger.info(f"Scheduled data processing task for tender UUID {tender_uuid}")

        except Exception as e:
            self.logger.error(f"Unexpected error syncing tender OCID {tender_ocid}: {e}", exc_info=True)

    def sync_all_tenders(self) -> int:
        """Syncs all tenders in the database."""
        self.logger.info("Syncing all tenders")
        processed_count = 0

        try:
            # Get OCIDs of tenders
            active_tender_ocids = self.tender_repo.get_active_tender_ocids(finished_tenders_statuses)
            self.logger.info(f"Found {len(active_tender_ocids)} tenders.")

            for ocid in active_tender_ocids:
                self.logger.info(f"Checking tender (OCID: {ocid})")
                self.sync_single_tender(ocid)
                processed_count += 1

            self.logger.info(
                f"Finished scheduling sync for subscribed tenders. Scheduled: {processed_count}/{len(active_tender_ocids)}")

        except Exception as e:
            self.logger.error(f"Error during subscribed tender sync: {e}", exc_info=True)

        return processed_count

    def crawl_tenders(self, pages_to_crawl: int = 1) -> int:
        """Crawls recent tenders using the discovery API and syncs them."""
        if pages_to_crawl < 1:
            self.logger.warning("pages_to_crawl must be at least 1.")
            return 0

        self.logger.info(f"Starting crawl for {pages_to_crawl} page(s)")
        processed_count = 0
        total_ocids_found = 0

        for page_num in range(pages_to_crawl):
            self.logger.info(f"Crawling search page {page_num}")
            tender_ocids = self.discovery_client.fetch_search_page_tender_ids(page=page_num)

            if tender_ocids is None:
                self.logger.error(f"Failed to fetch search page {page_num}. Stopping crawl.")
                break
            if not tender_ocids:
                self.logger.info(f"No tenders found on search page {page_num}. Stopping crawl.")
                break

            total_ocids_found += len(tender_ocids)
            self.logger.info(f"Found {len(tender_ocids)} tender OCIDs on page {page_num}")

            for tender_ocid in tender_ocids:
                self.sync_single_tender(tender_ocid)
                processed_count += 1

        self.logger.info(f"Crawl finished. Found {total_ocids_found} OCIDs across {pages_to_crawl} page(s). "
                         f"Scheduled processing for: {processed_count}")
        return processed_count
