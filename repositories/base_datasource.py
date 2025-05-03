from flask_sqlalchemy.session import Session

class BaseDatasource:
    def __init__(self, session: Session):
        self._session = session

    def flush(self) -> None:
        self._session.flush()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()