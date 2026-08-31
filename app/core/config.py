import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


AppEnvironment = Literal["development", "testing", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    PROJECT_NAME: str = Field(default="Scalable FastAPI Project")
    DESCRIPTION: str = Field(default="Core FastAPI application scaffold")
    VERSION: str = Field(default="0.1.0")

    ENVIRONMENT: AppEnvironment = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: LogLevel = Field(default="INFO")

    API_V1_PREFIX: str = Field(default="/api/v1")
    API_V2_PREFIX: str = Field(default="/api/v2")
    OPENAPI_URL: str = Field(default="/api/openapi.json")
    DOCS_URL: str = Field(default="/docs")
    REDOC_URL: str = Field(default="/redoc")
    DOCS_ENABLED: bool = Field(default=True)

    API_KEY: str = Field(default="dev-secret-key")
    AUTH_SECRET_KEY: str = Field(default="dev-auth-secret-key-change-me-32-bytes", min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=365)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1, le=1440)
    MAX_FAILED_LOGIN_ATTEMPTS: int = Field(default=5, ge=1, le=20)
    ACCOUNT_LOCK_MINUTES: int = Field(default=15, ge=1, le=1440)
    PASSWORD_MIN_LENGTH: int = Field(default=8, ge=8, le=128)
    RATE_LIMIT_PER_MINUTE: int = Field(default=120, ge=1, le=10000)
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    UPLOAD_DIR: str = Field(default="uploads")
    EXTERNAL_API_URL: str = Field(default="https://api.github.com")
    DATABASE_URL: str = Field(default="sqlite:///./app.db")
    AUTO_CREATE_TABLES: bool = Field(default=True)
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    SERVER_HOST: str = Field(default="127.0.0.1")
    SERVER_PORT: int = Field(default=8000, ge=1, le=65535)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator(
        "API_V1_PREFIX",
        "API_V2_PREFIX",
        "OPENAPI_URL",
        "DOCS_URL",
        "REDOC_URL",
    )
    @classmethod
    def validate_path_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("path settings must start with '/'")
        if len(value) > 1 and value.endswith("/"):
            raise ValueError("path settings must not end with '/'")
        return value

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_environment_settings(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
            if self.API_KEY == "dev-secret-key":
                raise ValueError("API_KEY must be changed in production")
            if self.AUTH_SECRET_KEY == "dev-auth-secret-key-change-me-32-bytes":
                raise ValueError("AUTH_SECRET_KEY must be changed in production")
        return self

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "testing"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def active_env_files(self) -> tuple[str, ...]:
        return _env_files_for(self.ENVIRONMENT)


def _active_environment() -> str:
    return (
        os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or _environment_from_base_env()
        or "development"
    )


def _environment_from_base_env() -> str | None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return None

    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "ENVIRONMENT":
            return value.strip().strip("'\"") or None

    return None


def _env_files_for(environment: str) -> tuple[str, ...]:
    return (
        str(BASE_DIR / ".env"),
        str(BASE_DIR / f".env.{environment}"),
    )


@lru_cache
def get_settings() -> Settings:
    environment = _active_environment()
    return Settings(ENVIRONMENT=environment, _env_file=_env_files_for(environment))


settings = get_settings()
