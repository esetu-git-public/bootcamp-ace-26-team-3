# Dashboard Frontend Integration

## Overview

This document describes the centralized API service layer that standardizes all frontend-backend communication for the Subscription Churn Predictor dashboard.

## API Service Module

**Location:** `frontend/src/services/api.js`

### Purpose

The API service module provides:
- ✅ Centralized API endpoint definitions
- ✅ Automatic authentication header injection (Bearer tokens)
- ✅ Consistent error handling and parsing
- ✅ Environment-based configuration support
- ✅ Type-safe endpoint wrappers

### Configuration

#### Environment Variables

Create a `.env.local` file in the `frontend/` directory to override defaults:

```bash
# .env.local
REACT_APP_API_URL=http://localhost:8000/api/v1
```

**Default:** `http://localhost:8000/api/v1`

See [frontend/.env.example](frontend/.env.example) for a template.

### Available Endpoints

#### Dashboard
- `getDashboardKPIs()` — KPI snapshot (total customers, churn count, revenue at risk)

#### Analytics
- `getChurnRiskDistribution()` — Distribution of customers by risk category
- `getChurnByIncome()` — Churn rate by income level
- `getChurnByDevice()` — Churn rate by device type
- `getChurnByPayment()` — Churn rate by payment mode
- `getChurnBySpend()` — Churn rate by monthly spend bucket
- `getChurnByTenure()` — Churn rate by tenure bucket
- `getChurnBySatisfaction()` — Churn rate by satisfaction score
- `getCustomerSegmentation()` — Customer segmentation statistics

#### Customer Management
- `getCustomers(page, limit, filters)` — Paginated customer list with filtering
- `getCustomerProfile(customerId)` — Individual customer profile
- `getCustomerPredictionHistory(customerId)` — Historical predictions for a customer

#### Predictions
- `runSinglePrediction(customerId)` — Run churn model on single customer
- `uploadBulkPredictions(file)` — Upload CSV for bulk predictions
- `getBulkPredictionStatus(jobId)` — Check job status and progress
- `getBulkPredictionPreview(jobId)` — Preview first 15 results

#### Reporting
- `exportReport(format, filters)` — Export filtered report as CSV/PDF/XLSX

#### Authentication
- `login(username, password)` — User login
- `signup(username, email, password, fullName)` — User registration

### Error Handling

All API functions throw errors with the following structure:

```javascript
{
  status: 401,  // HTTP status code
  message: "Could not validate credentials",
  endpoint: "/auth/login"
}
```

**Common Status Codes:**
- `401` — Authentication required (token missing/expired)
- `400` — Bad request (validation error)
- `404` — Resource not found
- `500` — Server error

### Usage Example

```javascript
import * as apiService from '../services/api';

async function loadDashboard() {
  try {
    const [kpis, risks, incomeData] = await Promise.all([
      apiService.getDashboardKPIs(),
      apiService.getChurnRiskDistribution(),
      apiService.getChurnByIncome()
    ]);
    setKpis(kpis);
    setRiskDistribution(risks);
    // ...
  } catch (err) {
    if (err.status === 401) {
      redirectToLogin();
    } else {
      showError(err.message);
    }
  }
}
```

## Migration Status

### Completed
- ✅ API service module created
- ✅ AnalyticsDashboard refactored to use centralized API service
- ✅ Environment configuration support added
- ✅ Bulk prediction polling improved
- ✅ Error handling standardized
- ✅ Login.js migrated to centralized API service
- ✅ SignUp.js migrated to centralized API service
- ✅ CustomerDirectory.js migrated to centralized API service
- ✅ CustomerProfile.js migrated to centralized API service
- ✅ ModelPerformance.js migrated to centralized API service

### Remaining Components (Future)
* None (All pages have been fully integrated with the centralized API service)*

## Authentication Flow

1. User logs in via `Login.js`
2. Backend returns `access_token` 
3. Token stored in `localStorage` as `access_token`
4. API service automatically injects `Authorization: Bearer {token}` header
5. If API returns 401, component handles logout

## Testing

To verify API integration locally:

```bash
# Terminal 1: Backend
cd backend
python run.py

# Terminal 2: Frontend
cd frontend
npm start

# Open http://localhost:3000
# Login with admin / admin123
```

## Files Modified

- `frontend/src/services/api.js` (new)
- `frontend/.env.example` (new)
- `frontend/src/pages/AnalyticsDashboard.js` (refactored)
