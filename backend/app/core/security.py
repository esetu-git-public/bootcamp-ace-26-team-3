import re
import bcrypt
from datetime import datetime, timedelta
from typing import Any, Union, List, Tuple
from jose import jwt
from passlib.hash import pbkdf2_sha256
from backend.app.core.config import settings


def is_strong_password(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password strength. Returns a tuple of (is_valid, list_of_errors).
    """
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character.")
        
    return len(errors) == 0, errors


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against the stored hash (supporting both bcrypt and pbkdf2_sha256).
    """
    try:
        # Check if it is a PBKDF2 hash (used by legacy/seeded users)
        if hashed_password.startswith("$pbkdf2-sha256$"):
            return pbkdf2_sha256.verify(plain_password, hashed_password)
        
        # Otherwise, assume bcrypt
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Generate bcrypt hash for a plain text password.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """
    Generate JWT access token.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


