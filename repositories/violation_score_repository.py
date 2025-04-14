from typing import Optional, Any

from sqlalchemy import Integer
from sqlalchemy.orm import Session

from models.violation_scores import ViolationScore
from repositories.base_repository import BaseRepository


class ViolationScoreRepository(BaseRepository[ViolationScore]):
    def __init__(self, session: Session):
        super().__init__(session)

    def get_by_id(self, id: Integer) -> Optional[ViolationScore]:
        """Get ViolationScore by id."""
        return self._session.query(ViolationScore).filter_by(id=id).first()

    def get_by_tender_id(self, tender_id: str) -> Optional[ViolationScore]:
        """Get ViolationScore by tender_id."""
        return self._session.query(ViolationScore).filter_by(tender_id=tender_id).first()

    def create(self, violation_score: ViolationScore) -> None:
        """Create a new ViolationScore, flush and commit the session."""
        self._session.add(violation_score)
        self._session.flush()
        self._session.commit()