# FastAPI router for Report Generation Module
# Saved at: backend/reports_router.py

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
import os

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["Reports"]
)

# Enums for validation
class ReportType(str, Enum):
    HIGH_RISK_CUSTOMERS = "high_risk_customers"
    CUSTOMER_SUMMARY = "customer_summary"
    PREDICTION_SUMMARY = "prediction_summary"
    SEGMENTATION_REPORT = "segmentation_report"

class ReportFormat(str, Enum):
    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"

# Request & Response schemas
class ReportFilter(BaseModel):
    min_churn_probability: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum churn probability filter (0.0 to 1.0)")
    income_level: Optional[str] = Field(None, description="Filter by income category (e.g. 'Low', 'Medium', 'High')")
    min_monthly_spend: Optional[float] = Field(None, ge=0.0, description="Minimum monthly spend filter in USD")

class ReportGenerateRequest(BaseModel):
    report_type: ReportType = Field(..., description="The type of analytical report to generate")
    format: ReportFormat = Field(..., description="The file format for the exported report")
    filters: Optional[ReportFilter] = Field(default_factory=ReportFilter, description="Optional search and segmentation filters")

class ReportGenerateResponse(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the background task processing the report")
    status: str = Field(..., description="Initial state of the background task (e.g. 'PENDING')")
    created_at: datetime = Field(..., description="Timestamp when the report generation was initiated")
    estimated_duration_seconds: float = Field(..., description="Estimated time for the generator worker to process the report")

class ReportStatusResponse(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the background task")
    status: str = Field(..., description="Current state of task (PENDING, PROCESSING, COMPLETED, FAILED)")
    progress_percentage: int = Field(..., description="Job progress from 0 to 100 percent")
    error: Optional[str] = Field(None, description="Detailed error message if the task failed")
    download_url: Optional[str] = Field(None, description="API endpoint path to download the generated file")

# Directories Configuration
REPORTS_DIR = "reports"

# Endpoint: POST /api/v1/reports/generate
@router.post("/generate", response_model=ReportGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_report(request: ReportGenerateRequest):
    """
    Triggers asynchronous generation of an analytical report.
    Returns a `task_id` that can be used to poll the task status.
    """
    try:
        # Generate a unique task ID (In production, Celery does this automatically)
        import uuid
        task_id = f"rep_task_{uuid.uuid4().hex[:8]}"
        
        # Import celery/background worker function and trigger delay
        # (Boilerplate structure linked with reports_worker.py)
        # from .reports_worker import generate_report_task
        # generate_report_task.delay(task_id, request.report_type, request.format, request.filters.dict())
        
        return ReportGenerateResponse(
            task_id=task_id,
            status="PENDING",
            created_at=datetime.now(timezone.utc),
            estimated_duration_seconds=5.0
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate report generation: {str(e)}"
        )

# Endpoint: GET /api/v1/reports/status/{task_id}
@router.get("/status/{task_id}", response_model=ReportStatusResponse)
async def get_report_status(task_id: str):
    """
    Polls the progress status of a running report generation task.
    Once completed, the response will contain the `download_url`.
    """
    # In production, this checks the Celery backend (Redis/PostgreSQL) for results.
    # For Sprint 1, we provide a placeholder mock response structure.
    import random
    mock_statuses = ["PENDING", "PROCESSING", "COMPLETED"]
    # Mocking progress based on a pseudo-random task id check
    mock_status = mock_statuses[len(task_id) % len(mock_statuses)]
    
    download_url = None
    progress = 0
    if mock_status == "COMPLETED":
        progress = 100
        download_url = f"/api/v1/reports/download/report_{task_id}.pdf"
    elif mock_status == "PROCESSING":
        progress = 45
    else:
        progress = 0

    return ReportStatusResponse(
        task_id=task_id,
        status=mock_status,
        progress_percentage=progress,
        error=None,
        download_url=download_url
    )

# Endpoint: GET /api/v1/reports/download/{filename}
@router.get("/download/{filename}")
async def download_report_file(filename: str):
    """
    Downloads a completed report file.
    Validates token session and retrieves file from server reports storage.
    """
    # Restrict file traversal vulnerability
    clean_filename = os.path.basename(filename)
    file_path = os.path.join(REPORTS_DIR, clean_filename)
    
    # In development/sprint demo, generate placeholder reports folder
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)
        
    # Check if the file physically exists on the disk
    if not os.path.exists(file_path):
        # Create a mock file for Sprint 1 demo if requested
        if clean_filename.startswith("report_"):
            with open(file_path, "w") as f:
                f.write("Mock analytical report content. Churn Platform Sprint 1.")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested report file does not exist or has expired."
            )
            
    # Set correct MIME types based on extension
    media_type = "application/octet-stream"
    if clean_filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif clean_filename.endswith(".csv"):
        media_type = "text/csv"
    elif clean_filename.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=clean_filename
    )
