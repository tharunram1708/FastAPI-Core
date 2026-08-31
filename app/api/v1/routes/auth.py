from fastapi import APIRouter, Response, status

from app.api.dependencies import CurrentActiveUserDep, DatabaseSessionDep
from app.schemas.response import ErrorResponse
from app.schemas.user import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginResponse,
    LogoutAllResponse,
    PasswordPolicyResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenRefreshResponse,
    UserCreate,
    UserLogin,
    UserRead,
    UserSessionRead,
)
from app.core.config import settings


router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "description": "User registered successfully.",
            "headers": {
                "X-Resource-ID": {
                    "description": "New user identifier.",
                    "schema": {"type": "string"},
                },
            },
        },
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        422: {"description": "Validation error."},
    },
    summary="Register user",
)
async def register_user(
    payload: UserCreate,
    response: Response,
    db: DatabaseSessionDep,
) -> UserRead:
    user = db.auth.register_user(payload)
    response.headers["X-Resource-ID"] = str(user.id)
    response.headers["Cache-Control"] = "no-store"
    return user


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "User authenticated successfully.",
            "headers": {
                "Cache-Control": {
                    "description": "Prevents token-bearing responses from being cached.",
                    "schema": {"type": "string"},
                },
            },
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        422: {"description": "Validation error."},
    },
    summary="Log in user",
)
async def login_user(
    payload: UserLogin,
    response: Response,
    db: DatabaseSessionDep,
) -> LoginResponse:
    login_response = db.auth.login_user(payload)
    response.headers["Cache-Control"] = "no-store"
    return login_response


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "Refresh token rotated successfully.",
            "headers": {
                "Cache-Control": {
                    "description": "Prevents token-bearing responses from being cached.",
                    "schema": {"type": "string"},
                },
            },
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        422: {"description": "Validation error."},
    },
    summary="Refresh tokens",
)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    response: Response,
    db: DatabaseSessionDep,
) -> TokenRefreshResponse:
    token_response = db.auth.refresh_tokens(payload)
    response.headers["Cache-Control"] = "no-store"
    return token_response


@router.get(
    "/me",
    response_model=UserRead,
    response_model_exclude_none=True,
    responses={
        status.HTTP_200_OK: {
            "description": "Current authenticated user returned successfully.",
            "headers": {
                "Cache-Control": {
                    "description": "Client caching policy.",
                    "schema": {"type": "string"},
                },
            },
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    },
    summary="Get current user",
)
async def get_current_user(
    current_user: CurrentActiveUserDep,
    response: Response,
) -> UserRead:
    response.headers["Cache-Control"] = "private, no-store"
    return current_user


@router.get(
    "/password-policy",
    response_model=PasswordPolicyResponse,
    summary="Get password policy",
)
async def get_password_policy() -> PasswordPolicyResponse:
    return PasswordPolicyResponse(min_length=settings.PASSWORD_MIN_LENGTH)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request password reset",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    response: Response,
    db: DatabaseSessionDep,
) -> ForgotPasswordResponse:
    reset_response = db.auth.forgot_password(payload)
    response.headers["Cache-Control"] = "no-store"
    return reset_response


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
    summary="Reset password",
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: DatabaseSessionDep,
) -> Response:
    db.auth.reset_password(payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/sessions",
    response_model=list[UserSessionRead],
    summary="List active sessions",
)
async def list_sessions(
    current_user: CurrentActiveUserDep,
    db: DatabaseSessionDep,
) -> list[UserSessionRead]:
    return db.auth.list_sessions(current_user)


@router.post(
    "/logout-all",
    response_model=LogoutAllResponse,
    summary="Logout from all devices",
)
async def logout_all_devices(
    current_user: CurrentActiveUserDep,
    db: DatabaseSessionDep,
) -> LogoutAllResponse:
    return db.auth.logout_all_devices(current_user)
