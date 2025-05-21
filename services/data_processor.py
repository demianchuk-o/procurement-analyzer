import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Type, Tuple
from decimal import Decimal

from celery_app import app as celery_app
from marshmallow import Schema


from api.legacy_prozorro_client import LegacyProzorroClient
from models import (TenderChange, TenderDocument, TenderDocumentChange, Award, AwardChange,
                    Bid, BidChange, Complaint, ComplaintChange)
from models.typing import ChangeT, EntityT
from repositories.tender_repository import TenderRepository
from schemas.award_schema import AwardSchema
from schemas.bid_schema import BidSchema
from schemas.complaint_schema import ComplaintSchema
from schemas.tender_document_schema import TenderDocumentSchema
from schemas.tender_schema import TenderSchema

from services.complaint_analysis_service import analyze_complaint_and_update_score
from util.db_context_manager import session_scope


@celery_app.task(queue="default", 
                 autoretry_for=(Exception,), 
                 retry_kwargs={'max_retries': 3})
def process_tender_data_task(tender_uuid: str,
                            tender_ocid: Optional[str],
                            date_modified_utc: datetime,
                             classifier_data: Optional[Dict[str,str]],
                             high_priority: bool = False) -> None:
    """
    Celery task to process tender data.
    """
    logger = logging.getLogger(__name__)
    from app import app
    with app.app_context(), session_scope() as session:
        try:
            tender_repo = TenderRepository(session)
            data_processor = DataProcessor(tender_repo)

            general_classifier_id = tender_repo.get_or_create_general_classifier_id(classifier_data)
            if classifier_data and not general_classifier_id:
                logger.warning(
                    f"Could not obtain general_classifier_id for tender UUID {tender_uuid} with data: {classifier_data}")


            data_processor.process_tender_data(
                tender_uuid=tender_uuid,
                tender_ocid=tender_ocid,
                date_modified_utc=date_modified_utc,
                general_classifier_id=general_classifier_id,
            )

            logger.info(f"Successfully processed tender UUID {tender_uuid}")

        except Exception as e:
            logger.error(f"Error processing tender UUID {tender_uuid}: {e}", exc_info=True)
            raise

class DataProcessor:
    def __init__(self, tender_repo: TenderRepository, high_priority: bool = False) -> None:
        self.logger = logging.getLogger(type(self).__name__)
        self.tender_repo = tender_repo
        self.legacy_client = LegacyProzorroClient()

        self.tender_schema = TenderSchema()
        self.tender_document_schema = TenderDocumentSchema()
        self.bid_schema = BidSchema()
        self.award_schema = AwardSchema()
        self.complaint_schema = ComplaintSchema()
        self._new_complaint_ids: List[str] = []

        self.high_priority = high_priority

    def _record_change(self,
                       change_model_cls: Type[ChangeT],
                       tender_id: str,
                       entity_fk_name: str, # 'tender_id', 'bid_id'
                       entity_fk_value: Any,
                       change_date: datetime,
                       field_name: str,
                       old_value: Any,
                       new_value: Any) -> None:
        """Generic method to record a change in a specific change table."""
        try:
            # ensure utc timezone
            if change_date.tzinfo is None:
                change_date = change_date.replace(tzinfo=timezone.utc)
            else:
                change_date = change_date.astimezone(timezone.utc)

            # format numeric values with two decimal places
            if isinstance(old_value, (int, float)):
                old_value_str = "{:.2f}".format(old_value)
            else:
                old_value_str = str(old_value) if old_value is not None else None

            if isinstance(new_value, (int, float)):
                new_value_str = "{:.2f}".format(new_value)
            else:
                new_value_str = str(new_value) if new_value is not None else None

            change_data = {
                entity_fk_name: entity_fk_value,
                "change_date": change_date,
                "tender_id": tender_id,
                "field_name": field_name,
                "old_value": old_value_str,
                "new_value": new_value_str,
            }

            change_record = change_model_cls(**change_data)
            self.tender_repo.record_change(change_record)
            self.logger.info(f"Recorded change for {entity_fk_name}={entity_fk_value}, field={field_name}")
        except Exception as e:
            self.logger.error(f"Failed to record change: {e}", exc_info=True)


    def _update_entity(self,
                       existing_entity: EntityT,
                       tender_uuid: str,
                       new_data_obj: EntityT,
                       fields_to_check: List[str],
                       change_model_cls: Type[ChangeT],
                       change_date: datetime,
                       entity_fk_name: str) -> bool:
        """
        Generic method to update an entity's fields and record changes.
        Handles 'deleted' status specifically.
        Returns True if any changes were made.
        """
        updated = False
        entity_id = getattr(existing_entity, 'id', '')
        new_status = getattr(new_data_obj, 'status', None)
        old_status = getattr(existing_entity, 'status', None)

        if new_status == 'deleted':
            if old_status != 'deleted':
                self.logger.info(f"Updating {existing_entity.__class__.__name__} {entity_id} status to 'deleted'")
                setattr(existing_entity, 'status', 'deleted')
                self._record_change(
                    change_model_cls=change_model_cls,
                    tender_id=tender_uuid,
                    entity_fk_name=entity_fk_name,
                    entity_fk_value=entity_id,
                    change_date=change_date,
                    field_name='status',
                    old_value=old_status,
                    new_value='deleted'
                )
                updated = True

            return updated

        for field in fields_to_check:
            if not hasattr(existing_entity, field) or not hasattr(new_data_obj, field):
                self.logger.warning(f"Field '{field}' not found in entity or new data, skipping.")
                continue

            old_value = getattr(existing_entity, field)
            new_value = getattr(new_data_obj, field)
            
            if isinstance(old_value, (int, float, Decimal)) and isinstance(new_value, (int, float, Decimal)):
                old_num = Decimal(old_value).quantize(Decimal('0.01'))
                new_num = Decimal(new_value).quantize(Decimal('0.01'))
                is_different = old_num != new_num

            # datetime comparison case
            if isinstance(old_value, datetime) and isinstance(new_value, datetime):
                 old_value_utc = old_value.astimezone(timezone.utc) if old_value and old_value.tzinfo else old_value
                 new_value_utc = new_value.astimezone(timezone.utc) if new_value and new_value.tzinfo else new_value

                 is_different = old_value_utc != new_value_utc
            else:
                 is_different = old_value != new_value

            if is_different:
                self.logger.info(f"Updating {existing_entity.__class__.__name__} {entity_id}: Field '{field}' changed from '{old_value}' to '{new_value}'")
                setattr(existing_entity, field, new_value)
                self._record_change(
                    change_model_cls=change_model_cls,
                    tender_id=tender_uuid,
                    entity_fk_name=entity_fk_name,
                    entity_fk_value=entity_id,
                    change_date=change_date,
                    field_name=field,
                    old_value=old_value,
                    new_value=new_value
                )
                updated = True

        return updated

    def _sync_related(self,
                      tender_id: str, # UUID
                      existing_related: List[EntityT],
                      incoming_data: List[Dict],
                      schema: Schema,
                      model_cls: Type[EntityT],
                      change_model_cls: Type[ChangeT],
                      fields_to_check: List[str],
                      change_date: datetime,
                      entity_fk_name: str
                      ) -> None:
        """
        Generic synchronizer for one-to-many related entities.
        """
        incoming_entities_map = {}

        for item_data in incoming_data:
            try:
                loaded_obj = schema.load(item_data)
                if loaded_obj and hasattr(loaded_obj, 'id'):
                     if hasattr(loaded_obj, 'tender_id'):
                          loaded_obj.tender_id = tender_id
                     incoming_entities_map[loaded_obj.id] = loaded_obj
                else:
                     self.logger.warning(f"Could not load or find ID for incoming {model_cls.__name__} data: {item_data}")
            except Exception as e:
                self.logger.error(f"Error loading {model_cls.__name__} with schema: {e}. Data: {item_data}", exc_info=True)


        existing_ids_map = {getattr(e, 'id'): e for e in existing_related}

        for entity_id, new_obj in incoming_entities_map.items():
            existing_entity = existing_ids_map.get(entity_id)

            if existing_entity:
                # Update existing
                self.logger.info(f"Updating existing {model_cls.__name__} {entity_id}")
                self._update_entity(
                    existing_entity=existing_entity,
                    tender_uuid=tender_id,
                    new_data_obj=new_obj,
                    fields_to_check=fields_to_check,
                    change_model_cls=change_model_cls,
                    change_date=change_date,
                    entity_fk_name=entity_fk_name
                )
            else:
                # Create new
                self.logger.info(f"Creating new {model_cls.__name__} {entity_id} for tender {tender_id}")
                self.tender_repo.add_entity(new_obj)

                if model_cls == Complaint:
                    self._new_complaint_ids.append(new_obj.id)

        self.tender_repo.flush()


    def process_tender_data(self,
                            tender_uuid: str,
                            tender_ocid: Optional[str],
                            date_modified_utc: datetime,
                            general_classifier_id: Optional[int]) -> bool:
        """
        Processes the full legacy tender data, updates DB, and records changes.
        Manages its own transaction within the provided session.
        """
        self.logger.info(f"Processing tender UUID {tender_uuid} (OCID: {tender_ocid})")

        legacy_details = self.legacy_client.fetch_tender_details(tender_uuid)
        if not legacy_details:
            self.logger.warning(f"Could not fetch legacy details for tender UUID {tender_uuid} (OCID {tender_ocid})")
            raise Exception(f"Could not fetch legacy details for tender UUID {tender_uuid} (OCID {tender_ocid})")

        if not tender_uuid:
            self.logger.error("Tender UUID is missing, cannot process.")
            return False

        try:
            loaded_tender = self.tender_schema.load(legacy_details)

            if 'value' in legacy_details and 'amount' in legacy_details['value']:
                loaded_tender.value_amount = legacy_details['value']['amount']

            if loaded_tender.id != tender_uuid:
                 self.logger.error(f"Loaded tender ID '{loaded_tender.id}' does not match expected UUID '{tender_uuid}'. Aborting.")
                 return False
        except Exception as e:
            self.logger.error(f"Failed to load tender data with schema for UUID {tender_uuid}: {e}", exc_info=True)
            return False

        try:
            if date_modified_utc.tzinfo is None:
                date_modified_utc = date_modified_utc.replace(tzinfo=timezone.utc)
            date_modified_utc = date_modified_utc.astimezone(timezone.utc)

            existing_tender = self.tender_repo.get_tender_with_relations(tender_uuid)
            is_new_tender = existing_tender is None


            tender_fields = [
                "date_created", "title", "value_amount", "status",
                "enquiry_period_start_date", "enquiry_period_end_date", "tender_period_start_date",
                "tender_period_end_date", "auction_period_start_date", "auction_period_end_date",
                "award_period_start_date", "award_period_end_date", "notice_publication_date"
            ]

            if is_new_tender:
                self.logger.info(f"Creating new tender UUID {tender_uuid}")

                # Explicitly set fields from discovery API
                loaded_tender.id = tender_uuid
                loaded_tender.ocid = tender_ocid
                loaded_tender.date_modified = date_modified_utc
                loaded_tender.general_classifier_id = general_classifier_id

                loaded_tender.documents = []
                loaded_tender.bids = []
                loaded_tender.awards = []
                loaded_tender.complaints = []

                self.tender_repo.add_entity(loaded_tender)
                self.tender_repo.flush()
                target_tender = loaded_tender
            else:
                self.logger.info(f"Updating existing tender UUID {tender_uuid}")
                target_tender = existing_tender

                self._update_entity(
                    existing_entity=target_tender,
                    tender_uuid=tender_uuid,
                    new_data_obj=loaded_tender,
                    fields_to_check=tender_fields,
                    change_model_cls=TenderChange,
                    change_date=date_modified_utc,
                    entity_fk_name='tender_id'
                )


                if target_tender.date_modified != date_modified_utc:
                     target_tender.date_modified = date_modified_utc
                if target_tender.general_classifier_id != general_classifier_id:
                     self._record_change(TenderChange, tender_uuid, 'tender_id', tender_uuid, date_modified_utc, 'general_classifier_id', target_tender.general_classifier_id, general_classifier_id)
                     target_tender.general_classifier_id = general_classifier_id

            change_date_for_related = date_modified_utc

            # Sync Documents
            self._sync_related(
                tender_id=tender_uuid,
                existing_related=list(target_tender.documents),
                incoming_data=legacy_details.get('documents', []),
                schema=self.tender_document_schema,
                model_cls=TenderDocument,
                change_model_cls=TenderDocumentChange,
                fields_to_check=["document_of", "title", "format", "url", "hash", "date_published", "date_modified"],
                change_date=change_date_for_related,
                entity_fk_name='document_id'
            )

            # Sync Bids
            self._sync_related(
                tender_id=tender_uuid,
                existing_related=list(target_tender.bids),
                incoming_data=legacy_details.get('bids', []),
                schema=self.bid_schema,
                model_cls=Bid,
                change_model_cls=BidChange,
                fields_to_check=["date", "status", "value_amount", "tenderer_id", "tenderer_legal_name"],
                change_date=change_date_for_related,
                entity_fk_name='bid_id'
            )

            # Sync Awards
            self._sync_related(
                tender_id=tender_uuid,
                existing_related=list(target_tender.awards),
                incoming_data=legacy_details.get('awards', []),
                schema=self.award_schema,
                model_cls=Award,
                change_model_cls=AwardChange,
                fields_to_check=["status", "title", "value_amount", "award_date", "complaint_period_start_date", "complaint_period_end_date"],
                change_date=change_date_for_related,
                entity_fk_name='award_id'
            )

            # Sync Complaints
            self._sync_related(
                tender_id=tender_uuid,
                existing_related=list(target_tender.complaints),
                incoming_data=legacy_details.get('complaints', []),
                schema=self.complaint_schema,
                model_cls=Complaint,
                change_model_cls=ComplaintChange,
                fields_to_check=["status", "title", "description", "date", "date_submitted", "date_answered", "type"],
                change_date=change_date_for_related,
                entity_fk_name='complaint_id'
            )

            self.tender_repo.commit()

            for complaint_id in self._new_complaint_ids:
                analyze_complaint_and_update_score.apply_async(
                    args=(tender_uuid, complaint_id),
                    queue='default',
                    priority=5 if self.high_priority else 0
                )

            self._new_complaint_ids.clear()

            self.logger.info(f"Successfully prepared changes for tender UUID {tender_uuid}")
            return True

        except Exception as e:
            self.tender_repo.rollback()
            self.logger.error(f"Error during processing tender UUID {tender_uuid}: {e}", exc_info=True)
            return False