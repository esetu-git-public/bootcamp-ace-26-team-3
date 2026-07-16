/**
 * Centralized API service for all dashboard requests.
 * Handles authentication, error responses, and environment configuration.
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const BACKEND_ORIGIN = API_BASE_URL.replace('/api/v1', '');

function notifyApiError(error) {
  if (typeof window === 'undefined') return;

  window.dispatchEvent(new CustomEvent('app:api-error', {
    detail: error,
  }));
}

/**
 * Decode a JWT and check if it's expired (client-side only, no signature verify).
 * Returns true if the token is missing, malformed, or past its exp claim.
 */
function isTokenExpired(token) {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    // exp is in seconds; Date.now() is in ms
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

/**
 * Get authorization headers with access token if available.
 */
function getAuthHeaders() {
  const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Parse error response and return user-friendly message.
 */
async function parseErrorResponse(response) {
  try {
    const data = await response.json();
    return data.detail || data.message || `Error: ${response.status} ${response.statusText || ''}`.trim();
  } catch {
    return `Error: ${response.status} ${response.statusText || ''}`.trim();
  }
}

/**
 * Generic fetch wrapper with error handling and auth.
 * Rejects with error on non-2xx responses; returns parsed JSON on success.
 * Proactively checks token expiry before making the request.
 */
async function request(endpoint, options = {}) {
  const token = localStorage.getItem('access_token');

  // Proactively check token expiry — avoids wasting a round-trip on a 401
  if (token && isTokenExpired(token)) {
    localStorage.removeItem('access_token');
    const error = { status: 401, message: 'Session expired. Please log in again.', endpoint };
    notifyApiError(error);
    throw error;
  }

  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    ...getAuthHeaders(),
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorMessage = await parseErrorResponse(response);
    const error = {
      status: response.status,
      message: errorMessage,
      endpoint,
    };
    notifyApiError(error);
    throw error;
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  return response.json();
}

/**
 * Dashboard KPI metrics
 */
export async function getDashboardKPIs() {
  return request('/dashboard/kpis');
}

/**
 * Churn risk distribution by category
 */
export async function getChurnRiskDistribution() {
  return request('/analytics/churn-risk-distribution');
}

/**
 * Churn rate by income level
 */
export async function getChurnByIncome() {
  return request('/analytics/churn-by-income');
}

/**
 * Churn rate by device type
 */
export async function getChurnByDevice() {
  return request('/analytics/churn-by-device');
}

/**
 * Churn rate by payment mode
 */
export async function getChurnByPayment() {
  return request('/analytics/churn-by-payment');
}

/**
 * Churn rate by spend bucket
 */
export async function getChurnBySpend() {
  return request('/analytics/churn-by-spend');
}

/**
 * Churn rate by tenure bucket
 */
export async function getChurnByTenure() {
  return request('/analytics/churn-by-tenure');
}

/**
 * Churn rate by satisfaction score
 */
export async function getChurnBySatisfaction() {
  return request('/analytics/churn-by-satisfaction');
}

/**
 * Customer segmentation statistics
 */
export async function getCustomerSegmentation() {
  return request('/analytics/customer-segmentation');
}

/**
 * Historical churn trends
 */
export async function getChurnTrends() {
  return request('/analytics/churn-trends');
}

/**
 * Churn risk velocity / acceleration
 */
export async function getRiskVelocity() {
  return request('/analytics/risk-velocity');
}


/**
 * List customers with pagination and filtering
 */
export async function getCustomers(page = 1, limit = 20, filters = {}) {
  const params = new URLSearchParams({
    page,
    limit,
  });

  if (filters.searchId) params.append('search_id', filters.searchId);
  if (filters.willCancel !== undefined && filters.willCancel !== null) {
    params.append('will_cancel', filters.willCancel);
  }

  // Handle singular or array filter values
  const appendFilter = (paramName, value) => {
    if (value === undefined || value === null) return;
    if (Array.isArray(value)) {
      value.forEach(val => params.append(paramName, val));
    } else {
      params.append(paramName, value);
    }
  };

  appendFilter('income_levels', filters.incomeLevel || filters.incomeLevels);
  appendFilter('device_types', filters.deviceType || filters.deviceTypes);
  appendFilter('payment_modes', filters.paymentMode || filters.paymentModes);
  appendFilter('risk_categories', filters.riskCategory || filters.riskCategories);
  if (filters.sortBy) params.append('sort_by', filters.sortBy);

  return request(`/customers?${params.toString()}`);
}

/**
 * Get single customer profile
 */
export async function getCustomerProfile(customerId) {
  return request(`/customers/${customerId}`);
}

/**
 * Get prediction history for a customer
 */
export async function getCustomerPredictionHistory(customerId) {
  return request(`/customers/${customerId}/history`);
}

/**
 * Run single customer prediction
 */
export async function runSinglePrediction(customerId) {
  return request(`/predictions/single/${customerId}`, { method: 'POST' });
}

/**
 * Run What-If risk simulation with behavior overrides
 */
export async function simulatePrediction(customerId, overrides) {
  return request(`/predictions/simulate/${customerId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(overrides),
  });
}


/**
 * Upload bulk predictions CSV file
 */
export async function uploadBulkPredictions(file) {
  const formData = new FormData();
  formData.append('file', file);

  const headers = getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/predictions/bulk`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    const errorMessage = await parseErrorResponse(response);
    const error = {
      status: response.status,
      message: errorMessage,
      endpoint: '/predictions/bulk',
    };
    notifyApiError(error);
    throw error;
  }

  return response.json();
}

/**
 * Get bulk prediction job status
 */
export async function getBulkPredictionStatus(jobId) {
  return request(`/predictions/bulk/status/${jobId}`);
}

/**
 * Get bulk prediction preview (first 15 records)
 */
export async function getBulkPredictionPreview(jobId) {
  return request(`/predictions/bulk/preview/${jobId}`);
}

/**
 * Get all bulk prediction jobs
 */
export async function getBulkJobs() {
  return request('/predictions/bulk/jobs');
}

/**
 * Get results of a bulk job (paginated)
 */
export async function getBulkJobResults(jobId, page = 1, limit = 15) {
  return request(`/predictions/bulk/jobs/${jobId}/results?page=${page}&limit=${limit}`);
}

/**
 * Get insights of a bulk job
 */
export async function getBulkJobInsights(jobId) {
  return request(`/predictions/bulk/jobs/${jobId}/insights`);
}

/**
 * Export bulk PDF report
 */
export async function exportBulkPdfReport(jobId) {
  const endpoint = `/reports/bulk/${jobId}/pdf`;
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const errorMessage = await parseErrorResponse(response);
    const error = {
      status: response.status,
      message: errorMessage,
      endpoint,
    };
    notifyApiError(error);
    throw error;
  }

  const disposition = response.headers?.get?.('Content-Disposition') || '';
  const filenameMatch = disposition.match(/filename="?([^"]+)"?/i);
  const filename = filenameMatch?.[1] || `bulk_insights_${jobId}.pdf`;
  const blob = await response.blob();

  return { blob, filename };
}


/**
 * Export report file with auth headers.
 */
export async function exportReport(format = 'csv', filters = {}) {
  const params = new URLSearchParams({ format });

  if (filters.jobId) params.append('job_id', filters.jobId);
  if (filters.riskCategory) params.append('risk_category', filters.riskCategory);
  if (filters.recommendationType) params.append('recommendation_type', filters.recommendationType);

  const endpoint = `/reports/export?${params.toString()}`;
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const errorMessage = await parseErrorResponse(response);
    const error = {
      status: response.status,
      message: errorMessage,
      endpoint,
    };
    notifyApiError(error);
    throw error;
  }

  const disposition = response.headers?.get?.('Content-Disposition') || '';
  const filenameMatch = disposition.match(/filename="?([^"]+)"?/i);
  const filename = filenameMatch?.[1] || `churn_report.${format}`;
  const blob = response.blob ? await response.blob() : new Blob([await response.text()]);

  return { blob, filename };
}

/**
 * Get model performance metrics
 */
export async function getModelMetrics() {
  return request('/model/metrics');
}

/**
 * User login
 */
export async function login(username, password) {
  return request('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
}

/**
 * User signup
 */
export async function signup(username, email, password, fullName = null) {
  return request('/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username,
      email,
      password,
      full_name: fullName,
    }),
  });
}

export async function listUsers() {
  return request('/auth/users');
}

/**
 * Delete a manager account (Admin only)
 */
export async function deleteUser(username) {
  return request(`/auth/users/${username}`, {
    method: 'DELETE',
  });
}

/**
 * Create a new retention intervention
 */
export async function createIntervention(data) {
  return request('/retention/interventions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

/**
 * List retention interventions for a customer
 */
export async function getInterventions(customerId = null, status = null) {
  const params = new URLSearchParams();
  if (customerId) params.append('customer_id', customerId);
  if (status) params.append('status', status);
  
  const queryStr = params.toString();
  return request(`/retention/interventions${queryStr ? `?${queryStr}` : ''}`);
}

/**
 * Update an existing retention intervention
 */
export async function updateIntervention(interventionId, data) {
  return request(`/retention/interventions/${interventionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

/**
 * Get backend origin for file downloads and other absolute URLs
 */
export function getBackendOrigin() {
  return BACKEND_ORIGIN;
}

/**
 * Get full API base URL
 */
export function getApiBaseUrl() {
  return API_BASE_URL;
}
