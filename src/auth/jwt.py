"""JWT token utilities."""
from datetime import datetime, timedelta
from typing import Optional
import jwt


SECRET_KEY = "temp-secret-key-for-testing"  # TODO: Move to config
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


class JWTManager:
    """JWT token manager."""

    @staticmethod
    def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        return create_access_token(data, expires_delta)

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and verify a JWT token."""
        return decode_access_token(token)

    @staticmethod
    def create_token_pair(user_id: str, role: str, tenant_id: Optional[str] = None) -> dict:
        """
        Create access and refresh token pair.

        Args:
            user_id: User UUID
            role: User role
            tenant_id: Optional tenant UUID

        Returns:
            Dict with access_token, refresh_token, token_type, expires_in
        """
        access_expires = timedelta(hours=1)
        refresh_expires = timedelta(days=7)

        token_data = {
            "user_id": user_id,
            "role": role,
            "tenant_id": tenant_id,
            "token_type": "access"
        }

        access_token = create_access_token(token_data, access_expires)

        refresh_data = {
            "user_id": user_id,
            "token_type": "refresh"
        }
        refresh_token = create_access_token(refresh_data, refresh_expires)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_expires.total_seconds())
        }

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string
            token_type: Expected token type ("access" or "refresh")

        Returns:
            Token payload if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            # Verify token type matches
            if payload.get("token_type") != token_type:
                return None

            return payload
        except jwt.PyJWTError:
            return None
