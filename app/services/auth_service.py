from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.authorization import effective_permissions
from app.core.config import settings
from app.core.exceptions import (
    AccountLockedError,
    DatabaseConstraintViolationError,
    DuplicateUserError,
    InactiveUserError,
    InvalidCredentialsError,
    PasswordResetError,
    RefreshTokenError,
)
from app.core.security import (
    create_access_token,
    generate_otp,
    generate_password_reset_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    hash_token,
    verify_password,
)
from app.models.enterprise import UserSession
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.enterprise_repository import EnterpriseRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginResponse,
    LogoutAllResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    UserCreate,
    UserLogin,
)


_DUMMY_PASSWORD_HASH = hash_password("Invalid-login-password1!")


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        enterprise_repository: EnterpriseRepository,
    ) -> None:
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository
        self.enterprise_repository = enterprise_repository

    def register_user(self, payload: UserCreate) -> User:
        if self.user_repository.username_or_email_exists(payload.username, payload.email):
            raise DuplicateUserError()

        try:
            return self.user_repository.create_user(
                username=payload.username,
                email=payload.email,
                password_hash=hash_password(payload.password),
                full_name=payload.full_name,
            )
        except DatabaseConstraintViolationError as exc:
            raise DuplicateUserError() from exc

    def login_user(self, payload: UserLogin) -> LoginResponse:
        user = self.user_repository.get_by_email(payload.email)
        if user is None:
            verify_password(payload.password, _DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError()
        if self._is_locked(user):
            raise AccountLockedError(
                "User account is locked until "
                f"{self._datetime_utc(user.locked_until).isoformat()}"
            )
        if not verify_password(payload.password, user.password_hash):
            self._record_failed_login(user)
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InactiveUserError()

        self._record_successful_login(user)
        return self._issue_token_pair(user)

    def refresh_tokens(self, payload: RefreshTokenRequest) -> LoginResponse:
        token_hash = hash_refresh_token(
            payload.refresh_token,
            secret_key=settings.AUTH_SECRET_KEY,
        )
        refresh_token = self.refresh_token_repository.get_by_hash(token_hash)
        if refresh_token is None:
            raise RefreshTokenError()
        if refresh_token.revoked_at is not None:
            raise RefreshTokenError()
        if self._datetime_utc(refresh_token.expires_at) <= self._now():
            raise RefreshTokenError()

        user = self.user_repository.get_user(refresh_token.user_id)
        if user is None:
            raise RefreshTokenError()
        if not user.is_active:
            raise InactiveUserError()

        session = self._get_session_by_refresh_token(refresh_token.id)
        if session is not None and session.revoked_at is not None:
            raise RefreshTokenError()

        return self._rotate_and_issue_token_pair(refresh_token, user, session)

    def forgot_password(self, payload: ForgotPasswordRequest) -> ForgotPasswordResponse:
        expires_delta = timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        user = self.user_repository.get_by_email(payload.email)
        if user is None:
            return ForgotPasswordResponse(
                message="If the account exists, password reset instructions were created.",
                expires_in=int(expires_delta.total_seconds()),
            )

        raw_token = generate_password_reset_token()
        otp = generate_otp()
        self.enterprise_repository.create_password_reset(
            user_id=user.id,
            token_hash=hash_token(raw_token, secret_key=settings.AUTH_SECRET_KEY),
            otp_hash=hash_token(otp, secret_key=settings.AUTH_SECRET_KEY),
            expires_at=self._now() + expires_delta,
        )
        self.enterprise_repository.create_notification(
            user_id=user.id,
            title="Password reset requested",
            message="A password reset OTP was generated for your account.",
            category="security",
            metadata={"delivery": "simulated-email"},
        )
        return ForgotPasswordResponse(
            message="Password reset instructions were created.",
            reset_token=raw_token,
            otp=otp,
            expires_in=int(expires_delta.total_seconds()),
        )

    def reset_password(self, payload: ResetPasswordRequest) -> None:
        token_hash = hash_token(payload.reset_token, secret_key=settings.AUTH_SECRET_KEY)
        reset_token = self.enterprise_repository.get_valid_password_reset(token_hash)
        if reset_token is None:
            raise PasswordResetError()
        expected_otp_hash = hash_token(payload.otp, secret_key=settings.AUTH_SECRET_KEY)
        if reset_token.otp_hash != expected_otp_hash:
            raise PasswordResetError()

        user = self.user_repository.get_user(reset_token.user_id)
        if user is None:
            raise PasswordResetError()
        if any(
            verify_password(payload.new_password, previous_hash)
            for previous_hash in user.password_history[-5:]
        ):
            raise PasswordResetError("New password cannot reuse a recent password")

        new_hash = hash_password(payload.new_password)
        reset_token.used_at = self._now()
        user.password_hash = new_hash
        user.password_history = [*user.password_history[-4:], new_hash]
        user.password_changed_at = self._now()
        user.failed_login_count = 0
        user.locked_until = None
        user.updated_at = self._now()
        self.enterprise_repository.revoke_user_sessions(user.id)
        self.refresh_token_repository.revoke_all_for_user(user.id)

    def list_sessions(self, user: User) -> list[UserSession]:
        return self.enterprise_repository.list_user_sessions(user.id)

    def logout_all_devices(self, user: User) -> LogoutAllResponse:
        revoked_sessions = self.enterprise_repository.revoke_user_sessions(user.id)
        self.refresh_token_repository.revoke_all_for_user(user.id)
        return LogoutAllResponse(revoked_sessions=revoked_sessions)

    def _rotate_and_issue_token_pair(
        self,
        current_refresh_token: RefreshToken,
        user: User,
        session: UserSession | None,
    ) -> LoginResponse:
        replacement_response, replacement_refresh_token = self._create_token_pair(
            user,
            session_id=session.id if session is not None else None,
        )
        self.refresh_token_repository.rotate_refresh_token(
            current_refresh_token,
            replacement_token=replacement_refresh_token,
        )
        if session is not None:
            session.refresh_token_id = replacement_refresh_token.id
            session.last_seen_at = self._now()
            session.updated_at = self._now()
        return replacement_response

    def _issue_token_pair(self, user: User) -> LoginResponse:
        refresh_token = self._create_refresh_token(user)
        session = self.enterprise_repository.sessions.create(
            {
                "user_id": user.id,
                "refresh_token_id": refresh_token.id,
                "last_seen_at": self._now(),
            }
        )
        return self._build_login_response(user, refresh_token, session.id)

    def _create_token_pair(
        self,
        user: User,
        session_id: UUID | None,
    ) -> tuple[LoginResponse, RefreshToken]:
        refresh_token = self._create_refresh_token(user)
        return self._build_login_response(user, refresh_token, session_id), refresh_token

    def _create_refresh_token(self, user: User) -> RefreshToken:
        raw_refresh_token = generate_refresh_token()
        setattr(self, "_last_raw_refresh_token", raw_refresh_token)
        return self.refresh_token_repository.create_refresh_token(
            user_id=user.id,
            token_hash=hash_refresh_token(
                raw_refresh_token,
                secret_key=settings.AUTH_SECRET_KEY,
            ),
            expires_at=self._now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

    def _build_login_response(
        self,
        user: User,
        refresh_token: RefreshToken,
        session_id: UUID | None,
    ) -> LoginResponse:
        access_expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expires_delta = self._datetime_utc(refresh_token.expires_at) - self._now()
        return LoginResponse(
            access_token=self._create_access_token(user, access_expires_delta, session_id),
            refresh_token=getattr(self, "_last_raw_refresh_token"),
            expires_in=int(access_expires_delta.total_seconds()),
            refresh_expires_in=max(1, int(refresh_expires_delta.total_seconds())),
            user=user,
        )

    def _create_access_token(
        self,
        user: User,
        expires_delta: timedelta,
        session_id: UUID | None,
    ) -> str:
        return create_access_token(
            subject=str(user.id),
            secret_key=settings.AUTH_SECRET_KEY,
            expires_delta=expires_delta,
            claims={
                "email": user.email,
                "username": user.username,
                "role": user.role,
                "permissions": sorted(effective_permissions(user.role, user.permissions)),
                "sid": str(session_id) if session_id is not None else None,
                "type": "access",
            },
        )

    def _get_session_by_refresh_token(self, refresh_token_id: UUID) -> UserSession | None:
        return self.enterprise_repository.session.scalar(
            select(UserSession).where(UserSession.refresh_token_id == refresh_token_id)
        )

    def _record_failed_login(self, user: User) -> None:
        user.failed_login_count += 1
        if user.failed_login_count >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = self._now() + timedelta(minutes=settings.ACCOUNT_LOCK_MINUTES)
        user.updated_at = self._now()

    def _record_successful_login(self, user: User) -> None:
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = self._now()
        user.updated_at = self._now()

    def _is_locked(self, user: User) -> bool:
        if user.locked_until is None:
            return False
        if self._datetime_utc(user.locked_until) <= self._now():
            user.failed_login_count = 0
            user.locked_until = None
            return False
        return True

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _datetime_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
