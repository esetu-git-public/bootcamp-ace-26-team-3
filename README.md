# Subscription Cancellation Prediction System (OTT/SaaS)

This project combines analytics, customer profiling, and churn prediction into a full-stack application for identifying customers at risk of cancelling their OTT/SaaS subscriptions.

## What's included

- A **FastAPI backend** with authentication, customer, analytics, prediction, model performance, report, and dashboard endpoints
- A **React frontend** with JWT-based authentication and four main views:
  - **Executive Analytics Dashboard** — KPI monitoring, churn risk charts, income/device/tenure breakdowns
  - **Customer Directory** — paginated listings, ID search, and multi-select risk/device/income/payment filters
  - **Profile Explorer** — detailed customer audit, on-demand prediction, local SHAP explainability, and prediction history timeline
  - **Model Performance** — live ML model diagnostics including accuracy, precision, recall, F1, ROC-AUC, confusion matrix, and feature importance
- A **Bulk Prediction Studio** for CSV upload and asynchronous churn scoring with preview and download
- A **centralized API service layer** (`api.js`) for all frontend–backend communication with JWT auth headers and unified error handling
- Rule-based churn scoring with retention recommendation outputs

## Project structure

```text
bootcamp-ace-26-team-3/
├── backend/                        # FastAPI backend
│   ├── requirements.txt            # Backend-specific dependency override (points to root)
│   └── app/
│       ├── main.py                 # Application entrypoint, CORS, router registration
│       ├── database.py             # SQLAlchemy engine and session setup
│       ├── models/                 # SQLAlchemy database models
│       │   ├── __init__.py         # Customer, ChurnPrediction, ModelMetric models
│       │   └── user.py             # User model
│       ├── routers/                # API route handlers
│       │   ├── analytics.py        # Churn analytics breakdown endpoints
│       │   ├── auth.py             # JWT login and signup
│       │   ├── customers.py        # Customer listing, profile, and history
│       │   ├── dashboard.py        # KPI summary endpoints
│       │   ├── model.py            # Model performance metrics endpoint
│       │   ├── predictions.py      # Single and bulk churn prediction
│       │   └── reports.py          # CSV/PDF/XLSX report export
│       └── schemas/                # Pydantic request/response schemas
│           ├── __init__.py
│           ├── common.py
│           └── user.py
├── frontend/                       # React frontend (Create React App)
│   ├── package.json
│   └── src/
│       ├── App.js                  # Root app with JWT auth state and view routing
│       ├── pages/
│       │   ├── Login.js            # JWT login form
│       │   ├── SignUp.js           # User registration form
│       │   ├── AnalyticsDashboard.js        # Executive dashboard with bulk prediction studio
│       │   ├── AnalyticsDashboard.test.js   # Dashboard unit tests
│       │   ├── CustomerDirectory.js         # Customer listing with filters
│       │   ├── CustomerProfile.js           # Profile explorer with SHAP and history
│       │   ├── ModelPerformance.js          # ML model diagnostics page
│       │   └── ModelPerformance.test.js     # Model performance unit tests
│       └── services/
│           ├── api.js              # Centralized API service (auth, fetch wrapper, all endpoints)
│           └── mlModel.js          # Client-side ML model utilities
├── database/                       # SQL schema and seed scripts
├── dataset/                        # Raw training/demo dataset
├── docs/                           # Integration notes and design documentation
│   └── DASHBOARD_INTEGRATION.md   # Frontend–backend integration guide
├── reports/                        # Exported prediction reports
├── requirements.txt                # Python dependencies (root environment)
└── README.md
```

## Getting started

### 1. Create and activate a Python virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS / Linux (bash/zsh):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

For local development and tests, the required dependencies (such as `pytest` and `pytest-asyncio`) are already included at the bottom of `requirements.txt` and were installed in the previous step, so no additional setup is required.

> **Note:** The React frontend requires Node.js and npm. If `npm` is not recognized, install Node.js from https://nodejs.org, restart PowerShell, and verify with:
>
> ```powershell
> node -v
> npm -v
> ```

### 3. Configure environment variables (optional)

By default the backend uses SQLite. To override:

On Windows PowerShell:

```powershell
$env:DATABASE_URL = 'sqlite:///./app.db'       # default (SQLite)
# $env:DATABASE_URL = 'postgresql://...'       # for PostgreSQL
```

On macOS / Linux (bash/zsh):

```bash
export DATABASE_URL='sqlite:///./app.db'       # default (SQLite)
# export DATABASE_URL='postgresql://...'       # for PostgreSQL
```

To point the frontend at a non-default backend URL, create `frontend/.env`:

```
REACT_APP_API_URL=http://localhost:8000/api/v1
```

### Running with a Single Command (Fastest)

You can run both the frontend and backend services concurrently using one of the following methods from the repository root:

* **Option A: Using NPM (Cross-Platform - All services in one terminal)**
  ```bash
  npm start
  ```
  *(Launches both services concurrently using a Node.js process runner.)*

* **Option B: Using PowerShell (Windows Only - Launches separate terminal windows)**
  ```powershell
  .\run.ps1
  ```
  *(Opens the backend and frontend in separate, persistent PowerShell windows.)*

* **Option C: Using Docker Compose (Cross-Platform - Containerized)**
  ```bash
  docker compose up --build
  ```
  > [!IMPORTANT]
  > Before running this, ensure **Docker Desktop** is open and fully started (the status bar/icon should show "Running" in green).

If you do not want to use Docker, you can run the application directly on your local system using **Option A** (`npm start`) or **Option B** (`.\run.ps1` for Windows).

### 4. Start the backend

From the repository root:

On Windows PowerShell:

```powershell
$env:PYTHONPATH = '.'
$env:DATABASE_URL = 'sqlite:///./app.db'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

On macOS / Linux (bash/zsh):

```bash
export PYTHONPATH=.
export DATABASE_URL='sqlite:///./app.db'
./.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

API available at:
- http://localhost:8000
- http://localhost:8000/api/docs  ← Interactive Swagger UI

### 5. Start the frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm start
```

UI available at:
- http://localhost:3000


## Using the app

### Authentication

The app requires a login before accessing any dashboard. Public signup has been disabled for security (Option B: Admin-Only Signup).
* A default administrator is seeded on database initialization: **Username:** `admin` (or Email `admin@company.com`), **Password:** `admin123`.
* New Customer Manager accounts can only be provisioned by the logged-in administrator via the **Manage Users** tab inside the dashboard.
* Logins support verification using either username or email address.

### Analytics Dashboard

After login, the dashboard shows:
- KPI summaries: total customers, active predictions, monthly spend, average risk score
- Churn risk distribution chart
- Breakdowns by income level, device type, spend bucket, tenure, and satisfaction score
- High-risk customer queue
- Bulk Prediction Studio for CSV upload and async scoring

### Customer Directory

Browse, search, and filter all registered customer profiles:
- Search by partial Customer ID
- Multi-select filters for Risk Level, Income Level, Device Type, and Payment Mode
- Will-Cancel status toggling (Stable vs. Churn)
- Quick links to jump to a customer's Profile Explorer

### Profile Explorer

Granular behavioral audit for an individual customer:
- Full demographic and subscription activity breakdown
- On-demand **Generate Model Prediction** execution
- Local SHAP explainability factor bars (feature contribution visualization)
- Personalized Retention Action Recommendations
- Prediction history timeline (audit log of past model runs)

### Model Performance

Live ML model diagnostics:
- Model version, accuracy, precision, recall, F1 score, and ROC-AUC
- Confusion matrix breakdown (TP, FP, TN, FN)
- Global feature importance bar chart
- Falls back to `backend/app/models/model_metrics.json` if no DB record exists

### Bulk Prediction Studio

Available from the Analytics Dashboard:
1. Upload a CSV file with the required columns
2. Monitor async job status and progress
3. Preview the first 15 predicted records
4. Download the full scored CSV report

**Required CSV columns:**

```text
customer_id,age,income_level,device_type,payment_mode,number_of_subscriptions,
tenure_months,monthly_total_spend,avg_usage_hours_per_week,app_switch_frequency,
customer_support_interactions,satisfaction_score,discount_used
```

## Model training and comparison

To improve generalization and check for overfitting and data leakage, we support training and comparing multiple classifiers (Logistic Regression, Random Forest, XGBoost, CatBoost, Gradient Boosting).

### 1. Model training notebook
For interactive experimentation, run the Jupyter Notebook:
- [notebooks/model_training_comparison.ipynb](file:///c:/Users/user/Downloads/Subscription%20Cancellation%20Prediction%20System%20%28OTTSaaS%29/bootcamp-ace-26-team-3/notebooks/model_training_comparison.ipynb)

### 2. Run model comparison script
To automate comparison and select/integrate the best leakage-free model:
```powershell
.\.venv\Scripts\python.exe backend/experiments/train_compare_models.py
```
This script will:
- Drop leakage features and identifier columns.
- Evaluate train-test gap and cross-validation scores.
- Select the best model (under 5% accuracy gap) and save versioned artifacts.
- Export comparison metrics, summary, and plots to `reports/`.

## Running tests

### Backend unit tests

From the `backend/` directory:

```powershell
$env:PYTHONPATH = "C:\Users\user\Downloads\Subscription Cancellation Prediction System (OTTSaaS)\bootcamp-ace-26-team-3"
.\.venv\Scripts\python.exe -m pytest
```

Test files:
- `tests/test_security_auth.py`
- `tests/test_bulk_predictions.py`
- `tests/test_probability_implementation.py`
- `tests/test_shap_explainability.py`

### Frontend unit tests

From the `frontend/` directory:

```powershell
npm test -- --watchAll=false
```

Test files:
- `src/pages/AnalyticsDashboard.test.js`
- `src/pages/ModelPerformance.test.js`

### Backend unit tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests
```

For full setup, architecture, and debugging details, see the [TDD & Unit Testing Documentation](file:///d:/Team-3/docs/TDD_TESTING_DOCUMENTATION.md) authored by **Manthena Sri Harshitha**.

## API reference

All routes are under `/api/v1`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/login` | Login and obtain JWT token (supports username or email lookup) |
| `POST` | `/auth/signup` | Register a new manager account (requires Administrator token) |
| `GET`  | `/dashboard/kpis` | KPI summary metrics |
| `GET`  | `/customers` | Paginated customer list with filters |
| `GET`  | `/customers/{id}` | Single customer profile |
| `GET`  | `/customers/{id}/history` | Prediction history for a customer |
| `POST` | `/predictions/single/{id}` | Run a single churn prediction |
| `POST` | `/predictions/bulk` | Upload CSV for bulk prediction |
| `GET`  | `/predictions/bulk/status/{job_id}` | Bulk job status |
| `GET`  | `/predictions/bulk/preview/{job_id}` | Preview bulk results |
| `GET`  | `/analytics/churn-risk-distribution` | Risk distribution breakdown |
| `GET`  | `/analytics/churn-by-income` | Churn rate by income level |
| `GET`  | `/analytics/churn-by-device` | Churn rate by device type |
| `GET`  | `/analytics/churn-by-payment` | Churn rate by payment mode |
| `GET`  | `/analytics/churn-by-spend` | Churn rate by spend bucket |
| `GET`  | `/analytics/churn-by-tenure` | Churn rate by tenure |
| `GET`  | `/analytics/churn-by-satisfaction` | Churn rate by satisfaction score |
| `GET`  | `/analytics/customer-segmentation` | Customer segmentation stats |
| `GET`  | `/model/metrics` | ML model performance metrics |
| `GET`  | `/reports/export` | Export report (CSV / PDF / XLSX) |

## Troubleshooting

- **Frontend can't reach backend** — confirm the backend is running on port 8000 and CORS is enabled
- **`npm start` fails** — run `npm install` first; ensure Node.js ≥ 16 is installed
- **Login returns 401** — ensure you are using the default admin account `admin`/`admin123` or your manager profile has been created by the system administrator
- **No model metrics shown** — place a `model_metrics.json` file under `backend/app/models/` or seed the `model_metrics` DB table
- **Switch from SQLite to PostgreSQL** — set `DATABASE_URL` to your connection string before starting the backend

