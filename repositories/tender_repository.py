from collections import defaultdict
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import Tender, GeneralClassifier, UserSubscription, Complaint, User
from models.typing import EntityT, ChangeT
from repositories.base_repository import BaseRepository


class TenderRepository(BaseRepository[Tender]):

    def __init__(self, session: Session):
        super().__init__(session)

    def get_by_id(self, id: str) -> Optional[Tender]:
        return self._session.get(Tender, id)

    def exists_by_id(self, id: str) -> bool:
        """Checks if a tender exists by its ID."""
        return self._session.query(Tender).filter(Tender.id == id).count() > 0

    def get_tender_with_relations(self, tender_uuid: str) -> Optional[Tender]:
         """Gets a tender and eagerly loads its relations needed for processing."""
         return self._session.query(Tender).options(
             selectinload(Tender.general_classifier),
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

    def get_modified_tenders_and_subscribed_users(self, since_date: datetime) -> Dict[str, List[str]]:
        """
        Fetches IDs of tenders modified since a given date and the emails
        of users subscribed to them.

        Returns:
            A dictionary mapping tender_id to a list of subscribed user emails.
            e.g., {'tender-id-1': ['user1@example.com', 'user2@example.com']}
        """
        stmt = (
            select(Tender.id, User.email)
            .join(UserSubscription, Tender.id == UserSubscription.tender_id)
            .join(User, UserSubscription.user_id == User.id)
            .where(Tender.date_modified > since_date)
            .order_by(Tender.id)
        )

        results = self._session.execute(stmt).all()

        tender_user_map = defaultdict(list)
        for tender_id, user_email in results:
            if user_email:
                tender_user_map[tender_id].append(user_email)

        return dict(tender_user_map)