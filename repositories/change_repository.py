from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from models.typing import ChangeT
from repositories.base_datasource import BaseDatasource


class ChangeRepository(BaseDatasource):
    def __init__(self, session: Session):
        super().__init__(session)

    def get_changes_since(self, change_cls: ChangeT, tender_id: str, since_date: datetime) -> List:
        """
        Retrieves changes for a specific tender since a given date.

        Args:
            change_cls: The SQLAlchemy model class for the change table (e.g., TenderChange, BidChange).
            tender_id: The ID of the tender to filter changes for.
            since_date: The datetime object representing the start of the time range.

        Returns:
            A list of change records (instances of the model_cls) for the specified tender and date range.
        """
        return self._session.query(change_cls).filter(
            change_cls.tender_id == tender_id,
            change_cls.change_date >= since_date
        ).all()
