from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.base import Base

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _sqlite_pragma(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    db_path = settings.state_db_path or (settings.project_root / "data" / "state.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
