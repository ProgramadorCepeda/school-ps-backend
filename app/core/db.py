from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and closes it after use."""
    with Session(engine) as session:
        yield session
