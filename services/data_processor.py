import logging

from sqlalchemy.exc import SQLAlchemyError

from db import db
from models import Tender, ItemClassification
from util.datetime_utils import parse_datetime


class DataProcessor:
    def __init__(self) -> None:
        self.logger = logging.getLogger(type(self).__name__)

    def process_tender(self, tender_data: dict) -> bool:
        tender_id = tender_data.get("id")
        self.logger.info(f"Processing tender {tender_id}")

        if not tender_id:
            self.logger.error("Tender ID is missing, skipping")
            return False

        existing_tender = Tender.query.get(tender_id)
        is_new_tender = existing_tender is None

        date_modified_str = tender_data.get("dateModified")
        date_modified = parse_datetime(date_modified_str)

        if existing_tender and existing_tender.date_modified and existing_tender.date_modified >= date_modified:
            self.logger.info(f"Tender {tender_id} is up-to-date, skipping")
            return False

        first_item_classification = tender_data.get("items", [])[0].get("classification")

        if not first_item_classification:
            self.logger.error(f"Not one item exists for tender {tender_id}, skipping")
            return False

        try:
            self._process_item_classification(tender_id, first_item_classification)
            if is_new_tender:
                tender = Tender(
                    id=tender_id,
                    date_created=parse_datetime(tender_data.get('date')),
                    date_modified=date_modified,
                    title=tender_data.get('title', ''),
                    value_amount=tender_data.get('value', {}).get('amount'),
                    status=tender_data.get('status'),
                    enquiry_period_start_date=parse_datetime(
                        tender_data.get('enquiryPeriod', {}).get('startDate')),
                    enquiry_period_end_date=parse_datetime(tender_data.get('enquiryPeriod', {}).get('endDate')),
                    tender_period_start_date=parse_datetime(tender_data.get('tenderPeriod', {}).get('startDate')),
                    tender_period_end_date=parse_datetime(tender_data.get('tenderPeriod', {}).get('endDate')),
                    auction_period_start_date=parse_datetime(
                        tender_data.get('auctionPeriod', {}).get('startDate')),
                    auction_period_end_date=parse_datetime(tender_data.get('auctionPeriod', {}).get('endDate')),
                    award_period_start_date=parse_datetime(tender_data.get('awardPeriod', {}).get('startDate')),
                    award_period_end_date=parse_datetime(tender_data.get('awardPeriod', {}).get('endDate')),
                    notice_publication_date=parse_datetime(tender_data.get('noticePublicationDate')),
                    item_classification_id=first_item_classification.get('id'),
                )
            else:
                existing_tender.date_modified = date_modified
                existing_tender.title = tender_data.get('title', '')
                existing_tender.value_amount = tender_data.get('value', {}).get('amount')
                existing_tender.status = tender_data.get('status')
                existing_tender.enquiry_period_start_date = parse_datetime(
                    tender_data.get('enquiryPeriod', {}).get('startDate'))
                existing_tender.enquiry_period_end_date = parse_datetime(
                    tender_data.get('enquiryPeriod', {}).get('endDate'))
                existing_tender.tender_period_start_date = parse_datetime(
                    tender_data.get('tenderPeriod', {}).get('startDate'))
                existing_tender.tender_period_end_date = parse_datetime(
                    tender_data.get('tenderPeriod', {}).get('endDate'))
                existing_tender.auction_period_start_date = parse_datetime(
                    tender_data.get('auctionPeriod', {}).get('startDate'))
                existing_tender.auction_period_end_date = parse_datetime(
                    tender_data.get('auctionPeriod', {}).get('endDate'))
                existing_tender.award_period_start_date = parse_datetime(
                    tender_data.get('awardPeriod', {}).get('startDate'))
                existing_tender.award_period_end_date = parse_datetime(
                    tender_data.get('awardPeriod', {}).get('endDate'))
                existing_tender.notice_publication_date = parse_datetime(tender_data.get('noticePublicationDate'))
                existing_tender.item_classification_id = first_item_classification.get('id')

            if 'documents' in tender_data:
                self._process_documents(tender_id, tender_data['documents'])

            if 'awards' in tender_data:
                self._process_awards(tender_id, tender_data['awards'])

            if 'bids' in tender_data:
                self._process_bids(tender_id, tender_data['bids'])

            if 'complaints' in tender_data:
                self._process_complaints(tender_id, tender_data['complaints'])

            db.session.commit()
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Database error processing tender {tender_id}: {e}")
            return False
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error processing tender {tender_id}: {e}")
            return False

        return True
    def _process_item_classification(self, tender_id: str, item_classification: dict) -> None:
        """Processing first item's classification, adding it to the database if it doesn't exist"""
        self.logger.info(f"Processing item classification for tender {tender_id}")

        item_classification_id = item_classification.get("id")

        item_classification_exists = ItemClassification.query.exists(item_classification_id)
        if item_classification_exists:
            self.logger.info(f"Item classification {item_classification_id} already exists")
            return
        else:
            item_classification = ItemClassification(
                id=item_classification_id,
                scheme=item_classification.get("scheme"),
                description=item_classification.get("description"),
            )
            db.session.add(item_classification)


    def _process_documents(self, tender_id: str, documents: list) -> None:
        self.logger.info(f"Processing documents for tender {tender_id}")
        # process documents (to be implemented)
        pass

    def _process_awards(self, tender_id: str, awards: list) -> None:
        self.logger.info(f"Processing awards for tender {tender_id}")
        # process awards (to be implemented)
        pass

    def _process_bids(self, tender_id: str, bids: list) -> None:
        self.logger.info(f"Processing bids for tender {tender_id}")
        # process bids (to be implemented)
        pass

    def _process_complaints(self, tender_id: str, complaints: list) -> None:
        self.logger.info(f"Processing complaints for tender {tender_id}")
        # process complaints (to be implemented)
        pass