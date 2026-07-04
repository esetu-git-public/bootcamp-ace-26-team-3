from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
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
except Exception as exc:
    print(f"Database initialization skipped: {exc}")

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
