"""Authentication router: register, login, current-user.

POST /v1/auth/register — create account + seller profile, return user + token.
POST /v1/auth/login    — JSON credentials, return token.
GET  /v1/auth/me       — bearer-protected, return current user.

Login accepts JSON (not multipart) to avoid a python-multipart dependency.
"""

from fastapi import APIRouter, HTTPException, status

from auto48.api.dependencies import CurrentUser, DbSession
from auto48.core.security import create_access_token
from auto48.models.auth_schemas import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from auto48.services.auth import authenticate, register_user

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: RegisterRequest, db: DbSession) -> RegisterResponse:
    """Create a new user account and matching seller profile."""
    try:
        user = await register_user(
            db,
            email=str(payload.email),
            password=payload.password,
            display_name=payload.display_name,
            seller_type=payload.seller_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    token = create_access_token(sub=str(user.id))
    return RegisterResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    """Verify email/password and return a JWT access token."""
    user = await authenticate(db, email=str(payload.email), password=payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(sub=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    """Return the currently authenticated user."""
    return UserResponse.model_validate(current_user)
