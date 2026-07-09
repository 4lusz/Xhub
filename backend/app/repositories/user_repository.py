"""Repository para o model User."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Acesso a dados de usuarios do XHub."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, User)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.db.scalars(statement).first()

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None
