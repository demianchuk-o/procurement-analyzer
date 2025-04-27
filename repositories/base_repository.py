from abc import ABC, abstractmethod
from typing import Optional, Generic, Any

from sqlalchemy.orm import Session

from models.typing import ModelT as T


class BaseRepository(ABC, Generic[T]):
    def __init__(self, session: Session):
        self._session = session

    @abstractmethod
    def get_by_id(self, id: Any) -> Optional[T]:
        pass

    def add(self, entity: T) -> None:
        self._session.add(entity)

    def flush(self) -> None:
        self._session.flush()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()