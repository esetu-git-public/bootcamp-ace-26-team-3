import sys
import subprocess
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime


def run_training_script():
    """
    Executes the model training script using the default data path.
    This function is designed to be called by the scheduler.
    """
    print(f"[{datetime.now()}] Starting scheduled model retraining...")
    
    try:
        python_executable = sys.executable
        # Assuming train_model.py is in the app directory
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "train_model.py")
        
        # Use the default data path from train_model.py's argparse
        # You can override this with a specific path if needed
        # e.g., "--data-path", "/path/to/latest/data.csv"
        
        # Generate a new model version based on the current date
        model_version = f"v{datetime.now().strftime('%Y.%m.%d')}"
        
        command = [python_executable, script_path, "--model-version", model_version, "--save-to-db"]
        
        # Using Popen to not block and to capture logs if needed
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print(f"[{datetime.now()}] Scheduled model retraining completed successfully for version {model_version}.")
            print("Output:\n", stdout)
        else:
            print(f"[{datetime.now()}] Scheduled model retraining failed for version {model_version}.")
            print("Error:\n", stderr)
            
    except Exception as e:
        print(f"[{datetime.now()}] An exception occurred during scheduled training: {e}")


scheduler = BackgroundScheduler(daemon=True)

# Schedule the job to run at 2:00 AM on the first day of every month
scheduler.add_job(run_training_script, CronTrigger(day=1, hour=2, minute=0))