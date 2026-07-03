import sys

print("=== Starting Backend Verification ===")

# Test basic imports
try:
    from fastapi import FastAPI
    print("[OK] fastapi imported successfully")
except ImportError as e:
    print(f"[ERROR] fastapi import failed: {e}")
    sys.exit(1)

# Test config setup
try:
    from backend.app.core.config import settings
    print(f"[OK] settings imported successfully. Project: '{settings.PROJECT_NAME}'")
except ImportError as e:
    print(f"[ERROR] config import failed: {e}")
    sys.exit(1)

# Test security utility
try:
    from backend.app.core.security import get_password_hash, verify_password
    pw_hash = get_password_hash("adminpassword123")
    assert verify_password("adminpassword123", pw_hash)
    assert not verify_password("wrongpassword", pw_hash)
    print("[OK] password hashing & verification works successfully")
except Exception as e:
    print(f"[ERROR] security utilities failed: {e}")
    sys.exit(1)

# Test DB session/models
try:
    from backend.app.db.session import Base
    from backend.app.models.user import User
    print("[OK] User SQLAlchemy DB model imports successfully")
except ImportError as e:
    print(f"[ERROR] DB models import failed: {e}")
    sys.exit(1)

# Test Schemas
try:
    from backend.app.schemas.user import UserCreate, UserResponse
    print("[OK] Pydantic user validation schemas import successfully")
except ImportError as e:
    print(f"[ERROR] Pydantic schemas import failed: {e}")
    sys.exit(1)

# Test API Routers
try:
    from backend.main import app
    print("[OK] main FastAPI app and routers loaded successfully")
except Exception as e:
    print(f"[ERROR] FastAPI routing initialization failed: {e}")
    sys.exit(1)

print("=== All Backend Modules Compiled and Verified Successfully! ===")
