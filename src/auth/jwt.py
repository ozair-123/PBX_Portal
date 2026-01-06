"""
JWT token generation and validation.

This module provides JWT authentication with:
- Access tokens (1 hour expiry)
- Refresh tokens (7 day expiry)
- HS256 algorithm (configurable via environment)
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from jose import JWTError, jwt
import os

# JWT Configuration from environment
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class JWTManager:
    """JWT token generation and validation manager."""

    @staticmethod
    def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.

        Args:
            data: Payload data to encode (typically user_id, role, tenant_id)
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT access token string

        Example:
            >>> manager = JWTManager()
            >>> token = manager.create_access_token(
            ...     data={"user_id": "123", "role": "tenant_admin", "tenant_id": "456"}
            ... )
            >>> # Returns: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict) -> str:
        """
        Create a JWT refresh token with longer expiration.

        Args:
            data: Payload data to encode (typically user_id only)

        Returns:
            Encoded JWT refresh token string

        Example:
            >>> manager = JWTManager()
            >>> token = manager.create_refresh_token(data={"user_id": "123"})
            >>> # Returns: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string to verify
            token_type: Expected token type ("access" or "refresh")

        Returns:
            Decoded token payload if valid, None if invalid

        Example:
            >>> manager = JWTManager()
            >>> token = manager.create_access_token(data={"user_id": "123"})
            >>> payload = manager.verify_token(token)
            >>> payload["user_id"]
            '123'
            >>> manager.verify_token("invalid_token")
            None
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            # Verify token type matches expected type
            if payload.get("type") != token_type:
                return None

            # Check expiration (jwt.decode already checks, but explicit check)
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                return None

            return payload
        except JWTError:
            return None

    @staticmethod
    def decode_token_without_verification(token: str) -> Optional[Dict]:
        """
        Decode a JWT token without verifying signature (for inspection only).

        ⚠️ WARNING: Do NOT use for authentication - this does not verify the token!
        Use verify_token() for authentication.

        Args:
            token: JWT token string to decode

        Returns:
            Decoded token payload (unverified)

        Example:
            >>> manager = JWTManager()
            >>> token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            >>> payload = manager.decode_token_without_verification(token)
            >>> # Returns payload dict (but signature not verified!)
        """
        try:
            # Decode without verification (for debugging/inspection only)
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False}
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def create_token_pair(user_id: str, role: str, tenant_id: Optional[str] = None) -> Dict[str, str]:
        """
        Create both access and refresh tokens for a user.

        Args:
            user_id: User ID (UUID string)
            role: User role (platform_admin, tenant_admin, support, end_user)
            tenant_id: Tenant ID (UUID string, None for platform_admin)

        Returns:
            Dictionary with access_token and refresh_token keys

        Example:
            >>> manager = JWTManager()
            >>> tokens = manager.create_token_pair(
            ...     user_id="123",
            ...     role="tenant_admin",
            ...     tenant_id="456"
            ... )
            >>> tokens.keys()
            dict_keys(['access_token', 'refresh_token', 'token_type', 'expires_in'])
        """
        # Access token payload includes full user context
        access_payload = {
            "user_id": user_id,
            "role": role,
        }
        if tenant_id:
            access_payload["tenant_id"] = tenant_id

        # Refresh token payload includes only user_id (minimal info)
        refresh_payload = {"user_id": user_id}

        return {
            "access_token": JWTManager.create_access_token(access_payload),
            "refresh_token": JWTManager.create_refresh_token(refresh_payload),
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        }
