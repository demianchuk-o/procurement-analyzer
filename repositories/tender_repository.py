from collections import defaultdict
from datetime import datetime
from typing import Optional, List, Dict, Tuple

from sqlalchemy import select
from sqlalchemy.sql.expression import func, and_
from sqlalchemy.orm import Session, selectinload

from models import Tender, GeneralClassifier, UserSubscription, Complaint, User
from models.typing import EntityT, ChangeT
from repositories.base_repository import BaseRepository

import re
OCID_PATTERN = re.compile(r"^UA-\d{4}-\d{2}-\d{2}-\d{6}-[a-z]$")

class TenderRepository(BaseRepository[Tender]):

    def __init__(self, session: Session):
        super().__init__(session)

    def get_by_id(self, id: str) -> Optional[Tender]:
        return self._session.get(Tender, id)

    def get_by_ocid(self, ocid: str) -> Optional[Tender]:
        return self._session.query(Tender).filter(Tender.ocid == ocid).first()

    def get_short_by_uuid(self, tender_uuid: str) -> Optional[Dict]:
        """
        Fetches a tender by its UUID and returns a short representation.
        :param tender_uuid: UUID of the tender.
        :return: A dictionary containing the tender ID and date modified.
        """
        short_data = self._session.query(Tender.id, Tender.date_modified).filter(
            Tender.id == tender_uuid
        ).first()

        if short_data:
            return {
                'id': short_data[0],
                'date_modified': short_data[1]
            }
        return None

    def search_tenders(self, search_term: str, page: int, per_page: int) -> Tuple[List[Dict], int]:
        query = self._session.query(Tender.id, Tender.date_modified, Tender.title)

        if OCID_PATTERN.match(search_term):
            query = query.filter(Tender.ocid == search_term)
        else:
            query = query.filter(Tender.title.ilike(f"%{search_term}%"))

        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        tenders = [
            {"tender_id": r[0], "date_modified": r[1], "title": r[2]}
            for r in rows
        ]
        return tenders, total

    def get_short_by_ocid_for_status_check(self, ocid: str) -> Optional[Dict]:
        """
        Fetches minimal info for a tender by OCID plus complaint counts:
          - total_complaints
          - processed_complaints (highlighted_keywords not empty)
        """
        row = (
            self._session
            .query(
                Tender.id.label('id'),
                func.count(Complaint.id).label('total_complaints'),
                func.count(Complaint.id)
                .filter(
                    and_(
                        Complaint.tender_id == Tender.id,
                        Complaint.highlighted_keywords.isnot(None),
                    )
                )
                .label('processed_complaints'),
            )
            .outerjoin(Complaint, Complaint.tender_id == Tender.id)
            .filter(Tender.ocid == ocid)
            .group_by(Tender.id)
            .first()
        )

        if not row:
            return None

        return {
            'id': row.id,
            'total_complaints': row.total_complaints,
            'processed_complaints': row.processed_complaints
        }

    def get_tenders_short(self, page: int, per_page: int) -> Tuple[List[Dict], int]:
        """
        Fetches tenders with pagination and returns a short representation.
        :param page: The current page number.
        :param per_page: Number of tenders per page.
        :return: A tuple containing a list of dictionaries with tender information
                 and the total number of tenders.
        """
        query = self._session.query(Tender.id, Tender.date_modified, Tender.title).order_by(Tender.date_modified.desc())
        total = query.count()  # Get total count before pagination
        short_data = query.offset((page - 1) * per_page).limit(per_page).all()

        tenders = []
        for tender in short_data:
            tenders.append({
                'tender_id': tender[0],
                'date_modified': tender[1],
                'title': tender[2]
            })
        return tenders, total

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
        """Creates a new GeneralClassifier. Commit is handled by the caller."""
        new_classification = GeneralClassifier(scheme=scheme, description=description)
        self._session.add(new_classification)

        return new_classification

    def get_or_create_general_classifier_id(self, classifier_data: Optional[dict]) -> Optional[int]:
        if not classifier_data:
            return None

        scheme = classifier_data.get('scheme')
        description = classifier_data.get('description')
        if not scheme or not description:
            return None

        classification = self.find_general_classifier(scheme=scheme, description=description)

        if classification:
            # flush if its a newly added classifier
            if not classification.id:
                self._session.flush()
            return classification.id
        else:
            new_classification = self.create_general_classifier(scheme=scheme, description=description)
            # flush to get the ID for the new classification
            self._session.flush()
            return new_classification.id

    def get_tenders_ocid_status(self) -> List[Tuple[str, str]]:
        """
        Fetches OCIDs and statuses of tenders as a list of tuples.
        """
        return self._session.query(Tender.ocid, Tender.status).filter(
            Tender.ocid.isnot(None)
        ).all()
        
    def get_active_tender_ocids(self, excluded_statuses: List[str]) -> List[str]:
        """
        Fetches OCIDs of tenders whose status is NOT in excluded_statuses.
        """
        results = self._session.query(Tender.ocid).filter(
            Tender.ocid.isnot(None),
            Tender.status.notin_(excluded_statuses)
        ).all()
        return [r[0] for r in results]

    def get_complaint_by_id(self, complaint_id: str) -> Optional[Complaint]:
        """
        Fetches a tender by its complaint ID.
        """
        return self._session.query(Complaint).filter(Complaint.id == complaint_id).first()

    def get_subscribed_tenders(self, user_id: int) -> list[Tender]:
        """
        Fetches all tenders that a user is subscribed to.
        :param user_id: ID of the user.
        :return: A list of tenders the user is subscribed to.
        """
        return (
            self._session
            .query(Tender)
            .join(UserSubscription, Tender.id == UserSubscription.tender_id)
            .filter(UserSubscription.user_id == user_id)
            .all()
        )

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