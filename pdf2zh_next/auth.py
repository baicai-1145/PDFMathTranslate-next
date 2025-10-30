from __future__ import annotations

import logging
import secrets
import sqlite3
from dataclasses import dataclass

from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from passlib.context import CryptContext

from pdf2zh_next.db import get_connection
from pdf2zh_next.db import init_db

logger = logging.getLogger(__name__)

SECURITY = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

init_db()


@dataclass(slots=True)
class User:
    id: int | None
    username: str
    display_name: str | None = None
    retention_days: int | None = None
    api_token: str | None = None
    is_guest: bool = False


class UserExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


GUEST_USER = User(
    id=None,
    username="guest",
    display_name="访客",
    retention_days=7,
    api_token=None,
    is_guest=True,
)


def _row_to_user(row) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        retention_days=row["retention_days"],
        api_token=row["api_token"],
        is_guest=False,
    )


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def register_user(username: str, password: str) -> tuple[User, str]:
    username = username.strip()
    if not username:
        raise ValueError("Username cannot be empty")
    hashed = pwd_context.hash(password)
    token = _generate_token()
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, display_name, api_token)
                VALUES (?, ?, ?, ?)
                """,
                (username, hashed, username, token),
            )
        except sqlite3.IntegrityError as exc:
            logger.warning("Failed to register user %s: %s", username, exc)
            raise UserExistsError from exc
        user_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
    if not row:
        raise RuntimeError("Failed to load newly created user")
    user = _row_to_user(row)
    return user, token


def authenticate_user(username: str, password: str) -> tuple[User, str]:
    username = username.strip()
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        )
        row = cursor.fetchone()
        if not row:
            raise InvalidCredentialsError
        if not pwd_context.verify(password, row["password_hash"]):
            raise InvalidCredentialsError
        token = _generate_token()
        conn.execute(
            "UPDATE users SET api_token = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (token, row["id"]),
        )
        conn.commit()
        row = dict(row)
        row["api_token"] = token
    return _row_to_user(row), token


def get_user_by_token(token: str) -> User | None:
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM users WHERE api_token = ?",
            (token,),
        )
        row = cursor.fetchone()
    if not row:
        return None
    return _row_to_user(row)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(SECURITY),
) -> User | None:
    if credentials is None or not credentials.credentials:
        return None
    token = credentials.credentials
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(  # invalid token should error out
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_user_or_guest(user: User | None = Depends(get_optional_user)) -> User:
    return user or GUEST_USER


__all__ = [
    "User",
    "GUEST_USER",
    "register_user",
    "authenticate_user",
    "get_current_user",
    "get_optional_user",
    "get_user_or_guest",
    "InvalidCredentialsError",
    "UserExistsError",
]
