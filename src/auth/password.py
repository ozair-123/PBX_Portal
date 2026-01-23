"""Password hashing utilities."""
import hashlib


class PasswordHasher:
    """Simple password hasher for testing."""

    @staticmethod
    def hash(password: str) -> str:
        """Hash a password."""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify(password: str, password_hash: str) -> bool:
        """Verify a password against a hash."""
        return PasswordHasher.hash(password) == password_hash


class PINHasher:
    """Simple PIN hasher for testing."""

    @staticmethod
    def hash(pin: str) -> str:
        """Hash a PIN."""
        return hashlib.sha256(pin.encode()).hexdigest()

    @staticmethod
    def verify(pin: str, pin_hash: str) -> bool:
        """Verify a PIN against a hash."""
        return PINHasher.hash(pin) == pin_hash
