from typing import Optional, Any, List, Dict

from sqlalchemy import Integer
from sqlalchemy.orm import Session

from models import Complaint
from models.violation_scores import ViolationScore
from repositories.base_repository import BaseRepository


class ViolationScoreRepository(BaseRepository[ViolationScore]):
    def __init__(self, session: Session):
        super().__init__(session)

    def get_by_id(self, id: Integer) -> Optional[ViolationScore]:
        """Get ViolationScore by id."""
        return self._session.query(ViolationScore).filter_by(id=id).first()

    def get_by_tender_id(self, tender_id: str) -> Optional[ViolationScore]:
        """Get ViolationScore by tender_id with a row-level lock."""
        return (
            self._session.query(ViolationScore)
            .filter_by(tender_id=tender_id)
            .with_for_update()
            .first()
        )

    def create(self, violation_score: ViolationScore) -> None:
        """Create a new ViolationScore, flush and commit the session."""
        self._session.add(violation_score)
        self._session.flush()
        self._session.commit()

    def update_complaint_highlighted_keywords(self, complaint: Complaint, highlighted_keywords: List[Dict]) -> None:
        """
        Updates the highlighted keywords in a complaint.
        """
        complaint.highlighted_keywords = highlighted_keywords
        self._session.commit()