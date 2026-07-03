from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base
from .routers import auth, dashboard, analytics, customers, predictions, reports, model

# Create database tables if they do not exist
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database initialization error (will proceed in fallback mode): {str(e)}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API services for the Subscription Cancellation Prediction System.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS Middleware to allow React Frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific frontend origins (e.g. localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Feature Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(model.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "api_version": "v1",
        "documentation": "/api/docs"
    }
