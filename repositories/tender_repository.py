from typing import Optional, List

from sqlalchemy.orm import Session, selectinload

from models import Tender, GeneralClassifier, UserSubscription, Complaint
from models.typing import EntityT, ChangeT
from repositories.base_repository import BaseRepository


class TenderRepository(BaseRepository[Tender]):

    def __init__(self, session: Session):
        super().__init__(session)

    def get_by_id(self, id: str) -> Optional[Tender]:
        return self._session.get(Tender, id)

    def get_tender_with_relations(self, tender_uuid: str) -> Optional[Tender]:
         """Gets a tender and eagerly loads its relations needed for processing."""
         return self._session.query(Tender).options(
             selectinload(Tender.bids),
             selectinload(Tender.awards),
             selectinload(Tender.documents),
             selectinload(Tender.complaints)
         ).get(tender_uuid)

    def add_entity(self, entity: EntityT) -> None:
        """Add any entity to the session."""
        self._session.add(entity)

    def record_change(self, change_entity: ChangeT) -> None:
        """Add a change record to the session."""
        self._session.add(change_entity)

    def find_general_classifier(self, scheme: str, description: str) -> Optional[GeneralClassifier]:
        """Finds a GeneralClassifier by scheme and description."""
        return self._session.query(GeneralClassifier).filter_by(
            scheme=scheme,
            description=description
        ).first()

    def create_general_classifier(self, scheme: str, description: str) -> GeneralClassifier:
        """Creates a new GeneralClassifier."""
        new_classification = GeneralClassifier(scheme=scheme, description=description)
        self._session.add(new_classification)
        self._session.flush()
        return new_classification

    def get_subscribed_tender_ocids(self) -> List[str]:
        """
        Fetches OCIDs of tenders that have user subscriptions.
        """
        return [
            row[0] for row in self._session.query(Tender.ocid)
            .join(UserSubscription, UserSubscription.tender_id == Tender.id)
            .filter(Tender.ocid.isnot(None))
            .distinct()
            .all()
        ]

    def get_complaint_by_id(self, complaint_id: str) -> Optional[Complaint]:
        """
        Fetches a tender by its complaint ID.
        """
        return self._session.query(Complaint).filter(Complaint.id == complaint_id).first()