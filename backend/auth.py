
import os
import jwt

from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database import get_connection

SECRET_KEY = os.getenv("GRIT_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "GRIT_SECRET_KEY is missing. Configure it before starting the API."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30

password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: str, role: str):
    expiry = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_MINUTES
    )

    payload = {
        "sub": user_id,
        "role": role,
        "exp": expiry
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")
        role = payload.get("role")

        if not user_id or role not in [
            "student", "interviewer", "admin"
        ]:
            raise HTTPException(401, "Invalid access token")

    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid or expired token")

    connection = get_connection()

    try:
        user = connection.execute(
            """
            SELECT id, name, email, role, active
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        ).fetchone()
    finally:
        connection.close()

    if not user or not user["active"] or user["role"] != role:
        raise HTTPException(401, "User account is inactive or invalid")

    return dict(user)


def require_role(*allowed_roles):
    def role_checker(user=Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource"
            )

        return user

    return role_checker
