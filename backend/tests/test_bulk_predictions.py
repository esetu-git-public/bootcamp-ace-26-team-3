import csv
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from unittest.mock import MagicMock

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile

from backend.app.routers import predictions, reports


def test_build_prediction_input_accepts_dashboard_headers():
    row = {
        "customer_id": "900",
        "age": "41",
        "income_level": "High",
        "device_type": "Android",
        "payment_mode": "UPI",
        "number_of_subscriptions": "3",
        "tenure_months": "18",
        "monthly_total_spend": "109.5",
        "avg_usage_hours_per_week": "21.25",
        "app_switch_frequency": "4",
        "customer_support_interactions": "2",
        "satisfaction_score": "8",
        "discount_used": "yes",
    }

    df = predictions._build_prediction_input(row)

    assert df.loc[0, "Age"] == 41
    assert df.loc[0, "Income_Level"] == "High"
    assert df.loc[0, "Discount_Used"] is True
    assert df.loc[0, "Monthly_Total_Spend"] == 109.5


def test_process_bulk_predictions_task_writes_real_results(tmp_path, monkeypatch):
    job_id = "job-test"
    monkeypatch.setattr(predictions, "RESULTS_DIR", str(tmp_path))
    monkeypatch.setattr(predictions.model_service, "champion_version", None)
    predictions.BULK_JOBS_DB.clear()
    predictions.BULK_JOBS_DB[job_id] = {
        "job_id": job_id,
        "status": "QUEUED",
        "total_records": 2,
        "processed_records": 0,
        "successful_records": 0,
        "failed_records": 0,
        "created_at": datetime.now(timezone.utc),
        "completed_at": None,
        "download_url": None,
    }
    upload = (
        "customer_id,age,income_level,device_type,payment_mode,number_of_subscriptions,"
        "tenure_months,monthly_total_spend,avg_usage_hours_per_week,app_switch_frequency,"
        "customer_support_interactions,satisfaction_score,discount_used\n"
        "100,34,Medium,Android,UPI,2,8,79.5,14.5,5,3,2,false\n"
        "101,45,High,iOS,Credit Card,1,20,120,25,2,1,8,true\n"
    ).encode("utf-8")

    predictions.process_bulk_predictions_task(job_id, upload)

    job = predictions.BULK_JOBS_DB[job_id]
    assert job["status"] == "COMPLETED"
    assert job["processed_records"] == 2
    assert job["successful_records"] == 2
    assert job["failed_records"] == 0
    assert job["download_url"] == f"/api/v1/reports/export?format=csv&job_id={job_id}"

    output_path = Path(tmp_path) / f"{job_id}.csv"
    with output_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert rows[0]["Customer ID"] == "100"
    assert rows[0]["Churn Probability"].endswith("%")
    assert rows[0]["Risk Category"] in {"Low", "Medium", "High"}


@pytest.mark.asyncio
async def test_get_bulk_status_returns_404_for_unknown_job():
    predictions.BULK_JOBS_DB.clear()

    with pytest.raises(HTTPException) as exc_info:
        await predictions.get_bulk_status("missing-job", current_user="admin")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_predict_bulk_rejects_empty_csv():
    upload = UploadFile(
        filename="customers.csv",
        file=BytesIO(b"customer_id,age\n"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await predictions.predict_bulk(
            BackgroundTasks(),
            file=upload,
            current_user="admin",
        )

    assert exc_info.value.status_code == 400
    assert "at least one customer record" in exc_info.value.detail


@pytest.mark.asyncio
async def test_export_bulk_report_returns_404_for_missing_job(tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "RESULTS_DIR", str(tmp_path))

    with pytest.raises(HTTPException) as exc_info:
        await reports.export_report(
            format="csv",
            job_id="missing-job",
            db=MagicMock(),
            current_user="admin",
        )

    assert exc_info.value.status_code == 404
