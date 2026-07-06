import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import AnalyticsDashboard from './AnalyticsDashboard';

describe('AnalyticsDashboard', () => {
  beforeEach(() => {
    global.fetch = jest.fn((url) => {
      if (url.includes('/dashboard/kpis')) {
        return Promise.resolve({ ok: true, json: async () => ({ total_customers: 120, predicted_churn_customers: 18, high_risk_customers: 7, average_churn_risk: 41, monthly_revenue_at_risk: 5400 }) });
      }
      if (url.includes('/analytics/churn-risk-distribution')) {
        return Promise.resolve({ ok: true, json: async () => [{ risk_category: 'High', customer_count: 8 }, { risk_category: 'Medium', customer_count: 10 }] });
      }
      if (url.includes('/analytics/churn-by-income')) {
        return Promise.resolve({ ok: true, json: async () => [{ income_level: 'Low', churn_rate: 12 }, { income_level: 'Medium', churn_rate: 24 }] });
      }
      if (url.includes('/analytics/churn-by-device')) {
        return Promise.resolve({ ok: true, json: async () => [{ device_type: 'Mobile', churn_rate: 20 }, { device_type: 'Desktop', churn_rate: 15 }] });
      }
      if (url.includes('/analytics/customer-segmentation')) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            { segment: 'High Risk', customer_count: 5, percentage: 10.0, average_churn_risk: 80.0 },
            { segment: 'Loyal', customer_count: 45, percentage: 90.0, average_churn_risk: 5.0 }
          ]
        });
      }
      if (url.includes('/customers?page=1&limit=6')) {
        return Promise.resolve({ ok: true, json: async () => ({ results: [{ customer_id: 'C1001', risk_category: 'High', monthly_total_spend: 80, tenure_months: 8, satisfaction_score: 6 }] }) });
      }
      if (url.includes('/predictions/bulk')) {
        return Promise.resolve({ ok: true, json: async () => ({ job_id: 'job-1', status: 'QUEUED', total_records: 2 }) });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
  });

  it('renders the bulk prediction studio controls', async () => {
    render(<AnalyticsDashboard />);

    expect(await screen.findByText(/Bulk prediction studio/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /run bulk prediction/i })).toBeInTheDocument();
  });

  it('uploads a CSV file to the bulk prediction endpoint', async () => {
    render(<AnalyticsDashboard />);

    await screen.findByText(/Bulk prediction studio/i);
    const file = new File(['customer_id,age\nC100,34\n'], 'customers.csv', { type: 'text/csv' });
    fireEvent.change(screen.getByLabelText(/bulk prediction csv/i), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /run bulk prediction/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/predictions/bulk',
        expect.objectContaining({ method: 'POST', body: expect.any(FormData) })
      );
    });
    expect(await screen.findByText(/Status: QUEUED/i)).toBeInTheDocument();
  });
});
