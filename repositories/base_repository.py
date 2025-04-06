from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic, List, Any
from sqlalchemy.orm import Session
from db import db

T = TypeVar('T', bound=db.Model)

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
