import logging
from datetime import datetime
from typing import Optional

from api.prozorro_client import ProzorroClient
from db import db
from models import UserSubscription, Tender


class CrawlerService:
    def __init__(self) -> None:
        self.client = ProzorroClient()
        self.logger = logging.getLogger(type(self).__name__)

    def sync_single_tender(self, tender_id) -> bool:
        self.logger.info(f"On-demand sync for tender {tender_id}")

        tender_details = self.client.fetch_tender_details(tender_id)
        if not tender_details:
            self.logger.warning(f"Could not fetch details for tender {tender_id}")
            return False

        # process tender details (to be implemented)
        return True

    def sync_subscribed_tenders(self) -> int:
        self.logger.info(f"Syncing subscribed tenders")

        subscribed_tenders = db.session.query(
            UserSubscription.tender_id \
                .distinct(UserSubscription.tender_id)\
                .all()
        )

        tender_ids = [item[0] for item in subscribed_tenders]

        self.logger.info(f"Found {len(tender_ids)} subscribed tenders")

        processed_count = 0
        for tender_id in tender_ids:
            success = self.sync_single_tender(tender_id)
            if success:
                processed_count += 1

        self.logger.info(f"Updated {processed_count} subbed tenders")
        return processed_count

    def crawl_tenders(self, offset: Optional[str] = None, limit: int = 100) -> int:

        tenders_list = self.client.fetch_all_tenders(start_offset=offset, limit=limit)
        self.logger.info(f"Fetched {len(tenders_list)} tenders from API")

        processed_count = 0
        skipped_count = 0

        for tender_meta in tenders_list:
            tender_id = tender_meta["id"]
            date_modified_str = tender_meta["dateModified"]

            if not tender_id or not date_modified_str:
                continue

            date_modified = datetime.fromisoformat(date_modified_str.replace("Z", "+00:00"))

            existing_tender = Tender.query\
                .filter_by(id=tender_id,
                           date_modified=date_modified)\
                .first()

            if existing_tender:
                self.logger.debug(f"Tender {tender_id} unchanged, skipping")
                skipped_count += 1
                continue

            self.logger.info(f"Processing tender {tender_id}")
            tender_details = self.client.fetch_tender_details(tender_id)
            if not tender_details:
                self.logger.warning(f"Could not fetch details for tender {tender_id}")
                continue

            # process tender details (to be implemented)
            success = True
            if success:
                processed_count += 1

        self.logger.info(f"Processed {processed_count} tenders, skipped {skipped_count} unchanged tenders")
        return processed_count