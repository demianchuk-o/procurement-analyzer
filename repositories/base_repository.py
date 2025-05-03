from abc import ABC, abstractmethod
from typing import Optional, Generic, Any

from sqlalchemy.orm import Session

from models.typing import ModelT as T
from repositories.base_datasource import BaseDatasource


class BaseRepository(BaseDatasource, ABC, Generic[T]):
    def __init__(self, session: Session):
        super().__init__(session)

    @abstractmethod
    def get_by_id(self, id: Any) -> Optional[T]:
        pass

    def add(self, entity: T) -> None:
        self._session.add(entity)