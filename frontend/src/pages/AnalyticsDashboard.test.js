import { render, screen } from '@testing-library/react';
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
      if (url.includes('/customers?page=1&limit=6')) {
        return Promise.resolve({ ok: true, json: async () => ({ results: [{ customer_id: 'C1001', risk_category: 'High', monthly_total_spend: 80, tenure_months: 8 }] }) });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
  });

  it('renders the bulk prediction studio controls', async () => {
    render(<AnalyticsDashboard />);

    expect(await screen.findByText(/Bulk prediction studio/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /run bulk prediction/i })).toBeInTheDocument();
  });
});
