from datetime import datetime
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.core.authorization import Permission, Role, normalize_role
from app.core.config import settings
from app.core.security import validate_password_policy

USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ValueError("value cannot be blank")
    return normalized


def _normalize_email(value: str) -> str:
    email = value.strip().casefold()
    if len(email) < 3:
        raise ValueError("email must be at least 3 characters")
    if "@" not in email or any(character.isspace() for character in email):
        raise ValueError("email must be a valid email-like value")
    local_part, _, domain = email.partition("@")
    if not local_part or "." not in domain:
        raise ValueError("email must include a local part and domain")
    return email


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        username = value.strip().casefold()
        if len(username) < 3:
            raise ValueError("username must be at least 3 characters")
        if not USERNAME_PATTERN.fullmatch(username):
            raise ValueError(
                "username must start with a letter and contain only letters, numbers, underscores, or hyphens"
            )
        return username

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        errors = validate_password_policy(value, min_length=settings.PASSWORD_MIN_LENGTH)
        if errors:
            raise ValueError("; ".join(errors))
        return value

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None
    otp: str | None = None
    expires_in: int


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(min_length=32, max_length=512)
    otp: str = Field(min_length=6, max_length=12)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        errors = validate_password_policy(value, min_length=settings.PASSWORD_MIN_LENGTH)
        if errors:
            raise ValueError("; ".join(errors))
        return value


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
    is_verified: bool | None = None
    role: Role | None = None
    permissions: list[Permission] | None = None

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


class UserRead(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str | None = None
    is_active: bool
    is_verified: bool
    role: str
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(ge=1)
    refresh_expires_in: int = Field(ge=1)
    user: UserRead


class UserSessionRead(BaseModel):
    id: UUID
    user_id: UUID
    user_agent: str | None
    ip_address: str | None
    revoked_at: datetime | None
    last_seen_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LogoutAllResponse(BaseModel):
    revoked_sessions: int
    message: str = "All active sessions were revoked"


class PasswordPolicyResponse(BaseModel):
    min_length: int
    require_lowercase: bool = True
    require_uppercase: bool = True
    require_number: bool = True
    require_symbol: bool = True


class RolePermissionsResponse(BaseModel):
    role: str
    permissions: list[str]


TokenRefreshResponse = LoginResponse
