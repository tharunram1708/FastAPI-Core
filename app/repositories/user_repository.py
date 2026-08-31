from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import SQLAlchemyRepository


class UserRepository(SQLAlchemyRepository[User]):
    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=User)

    def get_user(self, user_id: UUID) -> User | None:
        return self.get(user_id)

    def username_or_email_exists(self, username: str, email: str) -> bool:
        return self.exists(
            or_(
                func.lower(User.username) == username.casefold(),
                func.lower(User.email) == email.casefold(),
            )
        )

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(
            select(User).where(func.lower(User.email) == email.casefold())
        )

    def create_user(
        self,
        *,
        username: str,
        email: str,
        password_hash: str,
        full_name: str | None = None,
        role: str = "USER",
        permissions: list[str] | None = None,
    ) -> User:
        return self.create(
            {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "is_active": True,
                "is_verified": False,
                "role": role,
                "permissions": permissions or [],
                "password_history": [password_hash],
                "password_changed_at": datetime.now(timezone.utc),
            }
        )

    def list_users(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        return self.list(order_by=(User.created_at.desc(),), skip=skip, limit=limit)

    def update_user(self, user: User, data: dict) -> User:
        data["updated_at"] = datetime.now(timezone.utc)
        return self.update(user, data)
