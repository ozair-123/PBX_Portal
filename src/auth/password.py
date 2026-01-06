"""
Password hashing utilities using Argon2 and bcrypt.

This module provides secure password hashing for:
- User login passwords (Argon2id - preferred, bcrypt as fallback)
- Voicemail PINs (bcrypt)

Both are one-way hashes (irreversible).
"""

from passlib.context import CryptContext

# Primary context for user login passwords (Argon2id preferred, bcrypt fallback)
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,  # 3 iterations
    argon2__parallelism=4,  # 4 parallel threads
)

# Separate context for voicemail PINs (bcrypt only for compatibility)
pin_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


class PasswordHasher:
    """Password hashing and verification utility."""

    @staticmethod
    def hash(password: str) -> str:
        """
        Hash a password using Argon2id (preferred) or bcrypt.

        Args:
            password: Plain text password to hash

        Returns:
            Hashed password string

        Example:
            >>> hasher = PasswordHasher()
            >>> hashed = hasher.hash("SecurePassword123!")
            >>> # Returns: $argon2id$v=19$m=65536,t=3,p=4$...
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password to verify
            hashed: Hashed password string

        Returns:
            True if password matches hash, False otherwise

        Example:
            >>> hasher = PasswordHasher()
            >>> hashed = hasher.hash("SecurePassword123!")
            >>> hasher.verify("SecurePassword123!", hashed)
            True
            >>> hasher.verify("WrongPassword", hashed)
            False
        """
        try:
            return pwd_context.verify(password, hashed)
        except Exception:
            # Invalid hash format or verification error
            return False

    @staticmethod
    def needs_rehash(hashed: str) -> bool:
        """
        Check if a password hash needs to be rehashed with current settings.

        This is useful for upgrading from bcrypt to argon2 automatically.

        Args:
            hashed: Hashed password string

        Returns:
            True if hash should be regenerated with current settings

        Example:
            >>> hasher = PasswordHasher()
            >>> # Old bcrypt hash
            >>> old_hash = "$2b$12$..."
            >>> hasher.needs_rehash(old_hash)
            True  # Should upgrade to argon2
        """
        return pwd_context.needs_update(hashed)


class PINHasher:
    """Voicemail PIN hashing utility (bcrypt only for compatibility)."""

    @staticmethod
    def hash(pin: str) -> str:
        """
        Hash a voicemail PIN using bcrypt.

        Args:
            pin: Plain text PIN (4-8 digits)

        Returns:
            Hashed PIN string

        Example:
            >>> hasher = PINHasher()
            >>> hashed = hasher.hash("1234")
            >>> # Returns: $2b$12$...
        """
        return pin_context.hash(pin)

    @staticmethod
    def verify(pin: str, hashed: str) -> bool:
        """
        Verify a PIN against its hash.

        Args:
            pin: Plain text PIN to verify
            hashed: Hashed PIN string

        Returns:
            True if PIN matches hash, False otherwise

        Example:
            >>> hasher = PINHasher()
            >>> hashed = hasher.hash("1234")
            >>> hasher.verify("1234", hashed)
            True
            >>> hasher.verify("5678", hashed)
            False
        """
        try:
            return pin_context.verify(pin, hashed)
        except Exception:
            return False
