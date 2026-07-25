from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from slatesignal.core.security import (
    digest_token,
    hash_password,
    new_session_token,
    session_expiry,
    verify_password,
)
from slatesignal.domain.models import AuthSession, User


class EmailAlreadyExistsError(ValueError):
    pass


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_user(
        self,
        *,
        email: str,
        display_name: str,
        password: str,
        role: str = "user",
    ) -> User:
        user = User(
            email=email.strip().casefold(),
            display_name=display_name.strip(),
            password_hash=hash_password(password),
            role=role,
        )
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise EmailAlreadyExistsError from error
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User | None:
        statement = select(User).where(User.email == email.strip().casefold())
        user = self.db.scalar(statement)
        if not user or not verify_password(password, user.password_hash):
            return None
        return user

    def create_session(self, user: User) -> tuple[str, AuthSession]:
        raw_token, token_digest = new_session_token()
        session = AuthSession(
            token_digest=token_digest,
            user_id=user.id,
            expires_at=session_expiry(),
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return raw_token, session

    def resolve_session(self, token: str | None) -> User | None:
        if not token:
            return None
        statement = (
            select(AuthSession)
            .where(AuthSession.token_digest == digest_token(token))
            .join(AuthSession.user)
        )
        auth_session = self.db.scalar(statement)
        if not auth_session:
            return None
        expires_at = auth_session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            self.db.delete(auth_session)
            self.db.commit()
            return None
        return auth_session.user

    def revoke_session(self, token: str | None) -> None:
        if not token:
            return
        statement = delete(AuthSession).where(AuthSession.token_digest == digest_token(token))
        self.db.execute(statement)
        self.db.commit()
