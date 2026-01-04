"""Password hashing and validation utilities."""

from typing import cast

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password
    """
    return cast(str, pwd_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to verify against

    Returns:
        True if the password matches the hash, False otherwise
    """
    return cast(bool, pwd_context.verify(plain_password, hashed_password))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets minimum security requirements.

    Password requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit

    Args:
        password: The password to validate

    Returns:
        A tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not (has_upper and has_lower and has_digit):
        return False, "Password must contain uppercase, lowercase, and numbers"

    return True, ""
