from fastapi import status


class AppException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "APP_ERROR"
    detail = "Application error"
    headers: dict[str, str] | None = None

    def __init__(
        self,
        detail: str | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.detail = detail or self.detail
        self.headers = headers if headers is not None else self.headers
        super().__init__(self.detail)


class AuthenticationError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_FAILED"
    detail = "Invalid or missing API key"
    headers = {"WWW-Authenticate": "ApiKey"}


class InvalidCredentialsError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "INVALID_CREDENTIALS"
    detail = "Invalid email or password"
    headers = {"WWW-Authenticate": "Bearer"}


class AccessTokenError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "INVALID_ACCESS_TOKEN"
    detail = "Invalid or expired access token"
    headers = {"WWW-Authenticate": "Bearer"}


class RefreshTokenError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "INVALID_REFRESH_TOKEN"
    detail = "Invalid, revoked, or expired refresh token"
    headers = {"WWW-Authenticate": "Bearer"}


class InactiveUserError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "USER_INACTIVE"
    detail = "User account is inactive"


class AccountLockedError(AppException):
    status_code = status.HTTP_423_LOCKED
    error_code = "ACCOUNT_LOCKED"
    detail = "User account is temporarily locked"


class AuthorizationError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "AUTHORIZATION_FAILED"
    detail = "Insufficient role or permission"


class ResourceNotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"
    detail = "Resource not found"


class ItemNotFoundError(ResourceNotFoundError):
    error_code = "ITEM_NOT_FOUND"
    detail = "Item not found"


class DocumentNotFoundError(ResourceNotFoundError):
    error_code = "DOCUMENT_NOT_FOUND"
    detail = "Document not found"


class PasswordResetError(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "INVALID_PASSWORD_RESET"
    detail = "Invalid or expired password reset token"


class RateLimitExceededError(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"
    detail = "Too many requests"


class BusinessRuleViolationError(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "BUSINESS_RULE_VIOLATION"
    detail = "Business rule violation"


class DuplicateItemNameError(BusinessRuleViolationError):
    error_code = "DUPLICATE_ITEM_NAME"

    def __init__(self, name: str) -> None:
        super().__init__(f"An item named '{name}' already exists")


class DuplicateUserError(BusinessRuleViolationError):
    error_code = "DUPLICATE_USER"
    detail = "A user with this username or email already exists"


class DatabaseTransactionError(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "DATABASE_TRANSACTION_ERROR"
    detail = "Database transaction failed"


class DatabaseConstraintViolationError(BusinessRuleViolationError):
    error_code = "DATABASE_CONSTRAINT_VIOLATION"
    detail = "Database constraint violation"
