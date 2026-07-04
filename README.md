# Subscription Cancellation Prediction System (OTT/SaaS)

This system combines machine learning with business analytics to proactively identify customers at risk of cancelling their subscriptions. Built by ACE students (Team 3) during the Bootcamp.

## Project Structure

```text
bootcamp-ace-26-team-3/
│
├── backend/            # FastAPI (Python) backend APIs and business logic
│   └── app/
│       ├── main.py     # API routes, mock data, and prediction logs
│       └── schemas.py  # Pydantic input validation rules
│
├── frontend/           # React.js frontend interface and dashboards
│   ├── public/
│   │   └── index.html  # HTML root template
│   └── src/
│       ├── App.js      # Core React component wrapper
│       ├── index.js    # React DOM entrypoint
│       └── pages/
│           └── CustomerProfile.js  # Profile view & predictive insights dashboard
│
├── database/           # PostgreSQL configuration, schemas, and migrations
│   └── schema.sql      # Database schema (includes Prediction History table)
│
├── dataset/            # Machine learning dataset files (Subscription Fatigue.csv)
│
├── docs/               # System documentation and manuals
│   └── ui_wireframes.md# Standard user interface layouts and mockup designs
│
├── reports/            # Generated analytical and business reports
├── .gitignore          # Repository gitignore settings
├── README.md           # Project documentation and guide
└── requirements.txt    # Python library dependencies
```

---

## Setup & Running Instructions

### 1. Backend Setup (FastAPI)
1. Open a terminal and navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   * **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     venv\Scripts\activate
     ```
   * **macOS/Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
3. Install the required Python libraries:
   ```bash
   pip install -r ../requirements.txt
   ```

### 1.1. Editor & Linting Setup (Pyrefly)
If you use Pyrefly for import resolution/linting, the environment paths are configured in:
* **Root [pyrefly.toml](file:///c:/Users/user/Downloads/Subscription%20Cancellation%20Prediction%20System%20(OTTSaaS)/bootcamp-ace-26-team-3/pyrefly.toml)**: Points to `backend/venv/Scripts/python.exe`
* **Backend [backend/pyrefly.toml](file:///c:/Users/user/Downloads/Subscription%20Cancellation%20Prediction%20System%20(OTTSaaS)/bootcamp-ace-26-team-3/backend/pyrefly.toml)**: Points to `venv/Scripts/python.exe`

4. Run the backend local server:
   ```bash
   uvicorn app.main:app --reload
   ```
   * *The server will run on: **http://127.0.0.1:8000***

---

### 2. Frontend Setup (React.js)
Ensure you have downloaded and installed **Node.js (LTS version)** on your computer before proceeding.

1. Open a second, separate terminal window and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install the Node package dependencies:
   ```bash
   npm install
   ```
3. Start the React local development server:
   ```bash
   npm start
   ```
   * *The interface will automatically open on: **http://localhost:3000***

---

## Testing & Verifying the System

Since the backend operates with an in-memory test database, you must manually save a test customer profile on server startup before searching for them in React.

### Step 1: Add a Test Customer
1. Open your browser and navigate to: **[http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)** (FastAPI Swagger UI).
2. Click on the green **`POST /api/v1/customers`** endpoint.
3. Click **"Try it out"** on the right side.
4. Replace the existing body JSON with the following validated mock payload:
   ```json
   {
     "customer_id": "C10239",
     "age": 34,
     "income_level": "Medium",
     "device_type": "Mobile",
     "payment_mode": "UPI",
     "number_of_subscriptions": 3,
     "tenure_months": 12,
     "monthly_total_spend": 120.50,
     "avg_usage_hours_per_week": 2.4,
     "app_switch_frequency": 15,
     "customer_support_interactions": 6,
     "satisfaction_score": 2,
     "discount_used": false
   }
   ```
5. Click **"Execute"**. You should receive a `201` server response status.

### Step 2: Query and Run the Prediction in React
1. Navigate to **[http://localhost:3000](http://localhost:3000)**.
2. The page will load customer `C10239` automatically and display their demographics and usage stats.
3. Click the green **"Generate Churn Prediction"** button.
4. Verify the system results:
   * **Churn Prediction:** Changes to "LIKELY TO CANCEL" (Red Alert Box).
   * **Explainable AI:** Displays the contributing factor (`• Low satisfaction score`).
   * **Retention Recommendations:** Displays recommendation details advising discount code configurations or service desk escalations.
   * **Prediction History:** Updates with a chronological log of completed predictive queries.