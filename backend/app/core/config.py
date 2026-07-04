import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Subscription Churn Prediction Backend"
    API_V1_STR: str = "/api/v1"
    
    # Secret keys and cryptography
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkeychangeinproduction1234567890!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/churn_db")

    class Config:
        case_sensitive = True

settings = Settings()
