from typing import Optional

from sqlalchemy.orm import Session, selectinload

from models import Tender
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