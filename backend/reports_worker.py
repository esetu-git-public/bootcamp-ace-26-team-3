# Background task workers for Report Generation
# Saved at: backend/reports_worker.py

import os
import time
import logging
from datetime import datetime, timedelta

# Mock import of Celery app context
# from .celery_app import celery_app
# In production, this would be decorated with @celery_app.task(bind=True)

logger = logging.getLogger("reports_worker")
REPORTS_DIR = "reports"

def generate_report_task(task_id: str, report_type: str, file_format: str, filters: dict) -> str:
    """
    Asynchronous worker task that executes SQL queries, formats data into PDF/CSV/Excel,
    saves the output file, and stores progress in the task backend.
    """
    logger.info(f"Starting task {task_id} for report type {report_type} in {file_format} format.")
    
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)
        
    output_filename = f"report_{task_id}.{file_format}"
    file_path = os.path.join(REPORTS_DIR, output_filename)
    
    # 1. Simulate SQL DB Querying & Aggregation
    # In production, this runs optimized SQLAlchemy or raw SQL aggregates:
    # database.execute("SELECT ... WHERE ...")
    logger.info(f"Querying database with filters: {filters}")
    time.sleep(1.5) # Simulate database query delay
    
    # 2. Simulate PDF/CSV/Excel File Generation
    # Under the hood, we would use libraries like:
    # - reportlab (for PDF layout design)
    # - openpyxl (for Excel workbook styling)
    # - csv (for quick raw dumps)
    logger.info(f"Rendering report document into format {file_format}...")
    time.sleep(2.0) # Simulate file compilation
    
    # Creating a sample template content based on the format
    if file_format == "csv":
        with open(file_path, "w") as f:
            f.write("Customer_ID,Churn_Probability,Risk_Category,Recommendation\n")
            f.write("USR-1092,0.89,High,Offer 20% Discount\n")
            f.write("USR-4821,0.45,Medium,Personalized Email Outreach\n")
            f.write("USR-3021,0.12,Low,No Intervention Required\n")
    elif file_format == "xlsx":
        # In production, openpyxl creates Binary worksheets.
        # Writing mock workbook bytes here for the design template.
        with open(file_path, "wb") as f:
            f.write(b"PK\x03\x04...[Mock Excel Binary Content]...")
    else: # Default: pdf
        # In production, reportlab creates a clean, branded PDF canvas.
        with open(file_path, "w") as f:
            f.write("%PDF-1.4\n%[Mock PDF Binary Content/Metadata]\n")
            f.write(f"Title: Subscription Churn Analytical Report\n")
            f.write(f"Type: {report_type}\n")
            f.write(f"Generated at: {datetime.utcnow()}\n")
            f.write(f"Applied Filters: {filters}\n")
            
    logger.info(f"Task {task_id} completed successfully. Saved to {file_path}")
    return file_path


def cleanup_expired_reports():
    """
    Scheduled task (typically executed by Celery Beat every hour) 
    that cleans up generated reports older than 24 hours.
    """
    logger.info("Running automated report directory cleanup...")
    if not os.path.exists(REPORTS_DIR):
        return
        
    cutoff_time = datetime.now() - timedelta(hours=24)
    purged_count = 0
    
    for filename in os.listdir(REPORTS_DIR):
        file_path = os.path.join(REPORTS_DIR, filename)
        if os.path.isfile(file_path):
            file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
            if file_creation_time < cutoff_time:
                try:
                    os.remove(file_path)
                    logger.info(f"Purged expired report: {filename}")
                    purged_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {filename}: {str(e)}")
                    
    logger.info(f"Report directory cleanup completed. Purged {purged_count} file(s).")
