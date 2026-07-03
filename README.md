# Subscription Cancellation Prediction System (OTT/SaaS)

Bootcamp by ACE students Team 3. This system combines machine learning with business analytics to proactively identify customers at risk of cancelling their subscriptions.

## Project Structure

```text
subscription-churn-prediction/
│
├── backend/            # FastAPI (Python) backend APIs and business logic
├── frontend/           # React.js frontend dashboard and analytical charts
├── database/           # PostgreSQL configuration, schemas, and migrations
├── dataset/            # Machine learning dataset files
├── docs/               # System documentation and manuals
├── reports/            # Generated analytical and business reports
├── .gitignore          # Repository gitignore settings
├── README.md           # Project documentation and guide
└── requirements.txt    # Python library dependencies
```

## Setup Instructions

### Python Environment (Backend)
1. Navigate to the root directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
