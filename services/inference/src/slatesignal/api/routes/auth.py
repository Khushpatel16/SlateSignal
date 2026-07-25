import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from slatesignal.api.dependencies import CurrentUser, DbSession, OptionalUser
from slatesignal.core.config import get_settings
from slatesignal.core.rate_limit import rate_limiter
from slatesignal.domain.schemas import UserCreate, UserLogin, UserPublic
from slatesignal.repositories.auth import AuthRepository, EmailAlreadyExistsError

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.session_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limiter.dependency(limit=6, window_seconds=60))],
)
def register(
    payload: UserCreate,
    response: Response,
    db: DbSession,
    admin_bootstrap_token: Annotated[
        str | None,
        Header(alias="X-Admin-Bootstrap-Token"),
    ] = None,
) -> UserPublic:
    repository = AuthRepository(db)
    role = (
        "admin"
        if settings.admin_email
        and settings.admin_bootstrap_token
        and admin_bootstrap_token
        and payload.email.strip().casefold() == settings.admin_email.strip().casefold()
        and hmac.compare_digest(admin_bootstrap_token, settings.admin_bootstrap_token)
        else "user"
    )
    try:
        user = repository.create_user(
            email=str(payload.email),
            display_name=payload.display_name,
            password=payload.password,
            role=role,
        )
    except EmailAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error
    token, _ = repository.create_session(user)
    _set_session_cookie(response, token)
    return UserPublic.model_validate(user)


@router.post(
    "/login",
    response_model=UserPublic,
    dependencies=[Depends(rate_limiter.dependency(limit=8, window_seconds=60))],
)
def login(payload: UserLogin, response: Response, db: DbSession) -> UserPublic:
    repository = AuthRepository(db)
    user = repository.authenticate(str(payload.email), payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )
    token, _ = repository.create_session(user)
    _set_session_cookie(response, token)
    return UserPublic.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession) -> Response:
    AuthRepository(db).revoke_session(request.cookies.get(settings.cookie_name))
    response.delete_cookie(
        settings.cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserPublic)
def me(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(user)


@router.get("/session", response_model=UserPublic | None)
def session(user: OptionalUser) -> UserPublic | None:
    return UserPublic.model_validate(user) if user else None
