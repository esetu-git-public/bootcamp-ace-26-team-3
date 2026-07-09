import pytest
from datetime import timedelta
from jose import jwt
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core import security
from backend.app.routers import auth

# Initialize TestClient
client = TestClient(app)


class TestLoginConstraints:
    """Test login support for both username and email input."""

    def test_login_with_username_succeeds(self):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_with_email_succeeds(self):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin@company.com", "password": "admin123"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()



class TestPasswordStrength:
    """Test the strong password checker validation logic."""

    def test_valid_strong_password(self):
        # A valid strong password should pass all criteria
        valid, errors = security.is_strong_password("P@ssw0rd123!")
        assert valid is True
        assert len(errors) == 0

    def test_weak_password_too_short(self):
        # Passwords must be at least 8 characters
        valid, errors = security.is_strong_password("Pw1!")
        assert valid is False
        assert any("length" in err.lower() or "character" in err.lower() for err in errors)

    def test_weak_password_missing_uppercase(self):
        valid, errors = security.is_strong_password("p@ssw0rd123!")
        assert valid is False
        assert any("uppercase" in err.lower() for err in errors)

    def test_weak_password_missing_lowercase(self):
        valid, errors = security.is_strong_password("P@SSW0RD123!")
        assert valid is False
        assert any("lowercase" in err.lower() for err in errors)

    def test_weak_password_missing_digit(self):
        valid, errors = security.is_strong_password("P@ssword!")
        assert valid is False
        assert any("digit" in err.lower() or "number" in err.lower() for err in errors)

    def test_weak_password_missing_special_char(self):
        valid, errors = security.is_strong_password("P1assword123")
        assert valid is False
        assert any("special" in err.lower() for err in errors)


class TestSecurityUtilities:
    """Test the unified password hashing and JWT access token creation/verification."""

    def test_password_hash_and_verify(self):
        password = "SecurePassword123!"
        hashed = security.get_password_hash(password)
        
        # Verify correctness
        assert security.verify_password(password, hashed) is True
        # Verify incorrect password
        assert security.verify_password("wrong_password", hashed) is False

    def test_pbkdf2_compatibility(self):
        # Verify the new verify_password can verify existing pbkdf2_sha256 hashes
        from passlib.context import CryptContext
        legacy_context = CryptContext(schemes=["pbkdf2_sha256"])
        legacy_hash = legacy_context.hash("LegacyAdminPwd123!")
        
        assert security.verify_password("LegacyAdminPwd123!", legacy_hash) is True

    def test_create_access_token(self):
        subject = "test_user"
        token = security.create_access_token(subject, expires_delta=timedelta(minutes=10))
        
        # Decode and inspect token payload
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload.get("sub") == subject
        assert "exp" in payload


import uuid


def get_admin_token_headers() -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestSignupConstraints:
    """Integration tests for the /auth/signup endpoint validation constraints."""

    def test_signup_without_auth_fails(self):
        unique_id = uuid.uuid4().hex[:8]
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "username": f"user{unique_id}",
                "email": f"user_{unique_id}@example.com",
                "full_name": "New User",
                "password": "SecurePassword123!"
            }
        )
        assert response.status_code == 401

    def test_signup_with_weak_password_fails(self):
        headers = get_admin_token_headers()
        unique_id = uuid.uuid4().hex[:8]
        response = client.post(
            "/api/v1/auth/signup",
            headers=headers,
            json={
                "username": f"user{unique_id}",
                "email": f"user_{unique_id}@example.com",
                "full_name": "New User",
                "password": "weak"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "password" in data["detail"].lower()

    def test_signup_with_invalid_username_fails(self):
        headers = get_admin_token_headers()
        # Alphanumeric only, minimum 3 chars
        unique_id = uuid.uuid4().hex[:8]
        response_too_short = client.post(
            "/api/v1/auth/signup",
            headers=headers,
            json={
                "username": "ab",
                "email": f"short_{unique_id}@example.com",
                "full_name": "New User",
                "password": "SecurePassword123!"
            }
        )
        assert response_too_short.status_code == 400
        
        response_non_alphanumeric = client.post(
            "/api/v1/auth/signup",
            headers=headers,
            json={
                "username": f"user{unique_id}!",
                "email": f"nonalpha_{unique_id}@example.com",
                "full_name": "New User",
                "password": "SecurePassword123!"
            }
        )
        assert response_non_alphanumeric.status_code == 400


class TestUserListConstraints:
    """Integration tests for the GET /auth/users listing endpoint."""

    def test_list_users_without_auth_fails(self):
        response = client.get("/api/v1/auth/users")
        assert response.status_code == 401

    def test_list_users_by_non_admin_fails(self):
        unique_id = uuid.uuid4().hex[:8]
        admin_headers = get_admin_token_headers()
        
        # 1. Create a non-admin manager user first
        signup_res = client.post(
            "/api/v1/auth/signup",
            headers=admin_headers,
            json={
                "username": f"user{unique_id}",
                "email": f"user_{unique_id}@example.com",
                "full_name": "Regular Manager",
                "password": "SecurePassword123!"
            }
        )
        assert signup_res.status_code == 201
        
        # 2. Log in as that regular user
        login_res = client.post(
            "/api/v1/auth/login",
            json={"username": f"user{unique_id}", "password": "SecurePassword123!"}
        )
        assert login_res.status_code == 200
        user_token = login_res.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # 3. Attempt to list users
        list_res = client.get("/api/v1/auth/users", headers=user_headers)
        assert list_res.status_code == 403

    def test_list_users_by_admin_succeeds(self):
        headers = get_admin_token_headers()
        response = client.get("/api/v1/auth/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 1
        # Confirm admin is in the list
        usernames = [u["username"] for u in users]
        assert "admin" in usernames



