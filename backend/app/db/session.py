from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.app.core.config import settings

# Create engine
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modern SQLAlchemy 2.0 DeclarativeBase structure
class Base(DeclarativeBase):
    pass

# DB dependency to inject into routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
