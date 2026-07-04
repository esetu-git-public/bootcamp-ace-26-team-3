# Subscription Cancellation Prediction System (OTT/SaaS)

This project combines analytics, customer profiling, and churn prediction into a simple full-stack prototype for identifying customers at risk of cancelling their subscriptions.

## What’s included

- A FastAPI backend with customer, analytics, report, and prediction endpoints
- A React dashboard for KPI monitoring and customer risk review
- A bulk prediction studio that accepts CSV uploads and runs asynchronous churn scoring
- Rule-based churn scoring with recommendation outputs and preview/download support

## Project structure

```text
bootcamp-ace-26-team-3/
├── backend/                  # FastAPI backend and routers
│   └── app/
│       ├── main.py           # Application entrypoint
│       ├── routers/          # Analytics, auth, customer, dashboard, prediction, and report APIs
│       ├── schemas.py        # API response/request models
│       └── database.py       # SQLAlchemy engine and session setup
├── frontend/                 # React frontend
│   └── src/
│       ├── App.js            # App wrapper
│       └── pages/
│           └── AnalyticsDashboard.js  # Dashboard with bulk prediction UI
├── database/                 # SQL schema and backup scripts
├── dataset/                  # Raw training/demo dataset
├── docs/                     # UI and API design notes
├── reports/                  # Exported reports and results
├── requirements.txt          # Python dependencies for the repo root environment
└── README.md                 # Project documentation
```

## Getting started

### 1. Create and activate a Python environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
pip install -r backend\requirements.txt
```

> Note: The React frontend requires Node.js and npm. `npm` is not included in the Python virtual environment.
> If you see `npm : The term 'npm' is not recognized`, install Node.js from https://nodejs.org, restart PowerShell, and verify with:
>
> ```powershell
> node -v
> npm -v
> ```

### 3. Start the backend

From the repository root, run:

```powershell
$env:PYTHONPATH='.'
$env:DATABASE_URL='sqlite:///./app.db'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- http://localhost:8000
- http://localhost:8000/api/docs

### 4. Start the frontend

Open a second terminal and run:

```powershell
cd frontend
npm install
npm start
```

The UI will be available at:
- http://localhost:3000

## Using the app

### Analytics dashboard

Open the dashboard at http://localhost:3000 to view:
- KPI summaries
- Churn risk distribution
- Income and device split charts
- A high-risk customer queue

### Bulk prediction studio

The dashboard includes a Bulk Prediction Studio where you can upload a CSV file containing customer records and run asynchronous churn predictions.

Expected CSV columns include:

```text
customer_id,age,income_level,device_type,payment_mode,number_of_subscriptions,tenure_months,monthly_total_spend,avg_usage_hours_per_week,app_switch_frequency,customer_support_interactions,satisfaction_score,discount_used
```

After upload, the UI will show:
- job status and progress
- a preview of predicted results
- a download link for the generated CSV report

## API notes

The backend exposes prediction and analytics routes under `/api/v1`, including:
- `/api/v1/predictions/single/{customer_id}`
- `/api/v1/predictions/bulk`
- `/api/v1/predictions/bulk/status/{job_id}`
- `/api/v1/predictions/bulk/preview/{job_id}`

## Troubleshooting

- If the frontend cannot reach the backend, confirm that the backend server is still running on port 8000.
- If you want to switch away from the SQLite local setup, set `DATABASE_URL` to your preferred database connection string before starting the backend.
- If `npm start` shows a build warning, the app should still run locally in development mode.