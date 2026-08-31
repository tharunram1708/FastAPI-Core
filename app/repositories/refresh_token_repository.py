from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken
from app.repositories.base import SQLAlchemyRepository


class RefreshTokenRepository(SQLAlchemyRepository[RefreshToken]):
    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=RefreshToken)

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

    def create_refresh_token(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        return self.create(
            {
                "user_id": user_id,
                "token_hash": token_hash,
                "expires_at": expires_at,
            }
        )

    def rotate_refresh_token(
        self,
        current_token: RefreshToken,
        *,
        replacement_token: RefreshToken,
    ) -> RefreshToken:
        now = datetime.now(timezone.utc)
        current_token.revoked_at = now
        current_token.replaced_by_token_id = replacement_token.id
        current_token.updated_at = now
        self._flush()
        return current_token

    def revoke_all_for_user(self, user_id: UUID) -> int:
        now = datetime.now(timezone.utc)
        tokens = list(
            self.session.scalars(
                select(RefreshToken).where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None),
                )
            )
        )
        for token in tokens:
            token.revoked_at = now
            token.updated_at = now
        self._flush()
        return len(tokens)
