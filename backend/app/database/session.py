"""
Engine e sessionmaker do SQLAlchemy 2.0, mais a dependency `get_db`
usada pelas rotas do FastAPI.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI: abre uma sessao e garante o fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
