/**
 * Centralized API service for all dashboard requests.
 * Handles authentication, error responses, and environment configuration.
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const BACKEND_ORIGIN = API_BASE_URL.replace('/api/v1', '');

/**
 * Get authorization headers with access token if available.
 */
function getAuthHeaders() {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Parse error response and return user-friendly message.
 */
async function parseErrorResponse(response) {
  try {
    const data = await response.json();
    return data.detail || `Error: ${response.status} ${response.statusText}`;
  } catch {
    return `Error: ${response.status} ${response.statusText}`;
  }
}

/**
 * Generic fetch wrapper with error handling and auth.
 * Rejects with error on non-2xx responses; returns parsed JSON on success.
 */
async function request(endpoint, options = {}) {
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
    throw {
      status: response.status,
      message: errorMessage,
      endpoint,
    };
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
 * List customers with pagination and filtering
 */
export async function getCustomers(page = 1, limit = 20, filters = {}) {
  const params = new URLSearchParams({
    page,
    limit,
  });

  if (filters.searchId) params.append('search_id', filters.searchId);
  if (filters.incomeLevel) params.append('income_levels', filters.incomeLevel);
  if (filters.deviceType) params.append('device_types', filters.deviceType);
  if (filters.paymentMode) params.append('payment_modes', filters.paymentMode);
  if (filters.riskCategory) params.append('risk_categories', filters.riskCategory);
  if (filters.willCancel !== undefined && filters.willCancel !== null) {
    params.append('will_cancel', filters.willCancel);
  }

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
    throw {
      status: response.status,
      message: errorMessage,
      endpoint: '/predictions/bulk',
    };
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
 * Export report (CSV, PDF, XLSX)
 */
export async function exportReport(format = 'csv', filters = {}) {
  const params = new URLSearchParams({ format });

  if (filters.jobId) params.append('job_id', filters.jobId);
  if (filters.riskCategory) params.append('risk_category', filters.riskCategory);
  if (filters.recommendationType) params.append('recommendation_type', filters.recommendationType);

  return request(`/reports/export?${params.toString()}`);
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
