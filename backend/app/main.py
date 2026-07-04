from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .models.user import User
from .routers import analytics, auth, customers, dashboard, model, predictions, reports

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    Base.metadata.create_all(bind=engine)
    # Seed default admin user if none exists
    from .database import SessionLocal
    from passlib.context import CryptContext
    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.username == "admin").first()
        if not admin_exists:
            pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
            default_admin = User(
                username="admin",
                email="admin@company.com",
                full_name="Administrator",
                hashed_password=pwd_context.hash("admin123"),
                is_active=True
            )
            db.add(default_admin)
            db.commit()
            print("Default admin user seeded successfully.")
    finally:
        db.close()
except Exception as exc:
    print(f"Database initialization/seeding skipped: {exc}")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(model.router, prefix="/api/v1")


@app.get("/")
def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
