from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from slatesignal.core.config import get_settings
from slatesignal.core.database import get_db
from slatesignal.domain.models import User
from slatesignal.repositories.auth import AuthRepository

DbSession = Annotated[Session, Depends(get_db)]


def optional_user(
    db: DbSession,
    session_token: Annotated[
        str | None,
        Cookie(alias=get_settings().cookie_name),
    ] = None,
) -> User | None:
    return AuthRepository(db).resolve_session(session_token)


def current_user(user: Annotated[User | None, Depends(optional_user)]) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue.",
        )
    return user


def admin_user(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return user


CurrentUser = Annotated[User, Depends(current_user)]
AdminUser = Annotated[User, Depends(admin_user)]
OptionalUser = Annotated[User | None, Depends(optional_user)]
