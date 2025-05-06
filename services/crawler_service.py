import logging

from datetime import timezone
from typing import Optional

from api.discovery_prozorro_client import DiscoveryProzorroClient
from api.legacy_prozorro_client import LegacyProzorroClient
from services.data_processor import DataProcessor
from repositories.tender_repository import TenderRepository


class CrawlerService:
    def __init__(self, tender_repo: TenderRepository) -> None:
        self.discovery_client = DiscoveryProzorroClient()
        self.legacy_client = LegacyProzorroClient()
        self.tender_repo = tender_repo
        self.data_processor = DataProcessor(tender_repo)
        self.logger = logging.getLogger(type(self).__name__)

    def sync_single_tender(self, tender_ocid: str) -> bool:
        """
        Syncs a single tender using its OCID. Fetches data from both APIs if dateModified indicates a change.
        Manages DB transaction.
        """
        self.logger.info(f"Syncing single tender OCID {tender_ocid}")

        bridge_info = self.discovery_client.fetch_tender_bridge_info(tender_ocid)
        if not bridge_info:
            self.logger.warning(f"Could not fetch bridge info for tender OCID {tender_ocid}")
            return False

        tender_uuid = bridge_info.get('id')
        date_modified_from_bridge = bridge_info.get('dateModified')
        classifier_data = bridge_info.get('generalClassifier')

        if not tender_uuid or not date_modified_from_bridge:
             self.logger.error(f"Missing UUID or dateModified in bridge info for OCID {tender_ocid}")
             return False

        date_modified_utc = date_modified_from_bridge.astimezone(timezone.utc)

        try:
             existing_tender = self.tender_repo.get_by_id(tender_uuid)

             if (existing_tender and existing_tender.date_modified
                     and existing_tender.date_modified.astimezone(timezone.utc) >= date_modified_utc):
                 self.logger.debug(f"Tender UUID {tender_uuid} (OCID {tender_ocid}) unchanged (DB date: {existing_tender.date_modified}, API date: {date_modified_utc}), skipping detailed fetch.")
                 return True

             general_classifier_id = self._find_or_create_general_classifier(classifier_data)

             legacy_details = self.legacy_client.fetch_tender_details(tender_uuid)
             if not legacy_details:
                 self.logger.warning(f"Could not fetch legacy details for tender UUID {tender_uuid} (OCID {tender_ocid})")
                 self.tender_repo.rollback()
                 return False

             success = self.data_processor.process_tender_data(
                 tender_uuid=tender_uuid,
                 tender_ocid=tender_ocid,
                 date_modified_utc=date_modified_utc,
                 general_classifier_id=general_classifier_id,
                 legacy_details=legacy_details
             )

             if success:
                  self.logger.info(f"Successfully synced tender UUID {tender_uuid}")
             else:
                  self.logger.error(f"DataProcessor failed for tender UUID {tender_uuid}")

             return success

        except Exception as e:
             self.logger.error(f"Unexpected error syncing tender OCID {tender_ocid}: {e}", exc_info=True)
             self.tender_repo.rollback()
             return False


    def sync_subscribed_tenders(self) -> int:
        """Syncs all tenders that users are subscribed to."""
        self.logger.info("Syncing subscribed tenders")
        processed_count = 0

        try:
            # Get (UUID, OCID) pairs directly with a single join query
            subscribed_tender_ocids = self.tender_repo.get_subscribed_tender_ocids()
            self.logger.info(f"Found {len(subscribed_tender_ocids)} subscribed tenders.")

            for tender_ocid in subscribed_tender_ocids:
                self.logger.info(f"Checking subscribed tender (OCID: {tender_ocid})")
                success = self.sync_single_tender(tender_ocid)
                if success:
                    processed_count += 1
                else:
                    self.logger.warning(f"Failed to sync subscribed tender OCID {tender_ocid}")

            self.logger.info(
                f"Finished syncing subscribed tenders. Processed: {processed_count}/{len(subscribed_tender_ocids)}")

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
                success = self.sync_single_tender(tender_ocid)
                if success:
                     processed_count += 1
                else:
                     self.logger.warning(f"Failed processing tender OCID {tender_ocid} during crawl.")

        self.logger.info(f"Crawl finished. Found {total_ocids_found} OCIDs across {pages_to_crawl} page(s). "
                         f"Successfully processed/checked: {processed_count}")
        return processed_count

    def _find_or_create_general_classifier(self, classifier_data: dict) -> Optional[int]:
        """Finds or creates a GeneralClassifier record and returns its ID."""
        if not classifier_data:
            return None

        scheme = classifier_data.get('scheme')
        description = classifier_data.get('description')
        if not scheme or not description:
             self.logger.warning("Missing scheme or description in classifier data")
             return None


        classification = self.tender_repo.find_general_classifier(scheme=scheme, description=description)

        if classification:
            return classification.id
        else:
            new_classification = self.tender_repo.create_general_classifier(scheme=scheme, description=description)
            self.tender_repo.commit()
            self.logger.info(f"Prepared new GeneralClassifier: ID {new_classification.id}, Scheme: {scheme}")
            return new_classification.id

