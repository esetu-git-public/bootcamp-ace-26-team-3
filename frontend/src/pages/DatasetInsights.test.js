import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import DatasetInsights from './DatasetInsights';

// Mock the api service
jest.mock('../services/api', () => ({
  getBulkJobInsights: jest.fn(),
  getBulkJobResults: jest.fn(),
  exportBulkPdfReport: jest.fn(),
  exportReport: jest.fn()
}));

const api = require('../services/api');

describe('DatasetInsights', () => {
  const mockNotify = jest.fn();
  const mockViewChange = jest.fn();
  const mockSetSelectedJobId = jest.fn();
  
  const mockInsights = {
    kpis: {
      total_customers: 2,
      predicted_churn_customers: 1,
      high_risk_customers: 1,
      average_churn_risk: 50.0,
      average_satisfaction: 5.0,
      average_monthly_spend: 100.0,
      average_tenure_months: 12.0,
      monthly_revenue_at_risk: 120.0
    },
    risk_distribution: [
      { risk_category: 'Low', customer_count: 1, percentage: 50.0 },
      { risk_category: 'Medium', customer_count: 0, percentage: 0.0 },
      { risk_category: 'High', customer_count: 1, percentage: 50.0 }
    ],
    churn_probability_buckets: [
      { bucket: '0-10%', count: 1 },
      { bucket: '90-100%', count: 1 }
    ],
    device_risk_breakdown: [],
    payment_risk_breakdown: [],
    income_risk_breakdown: [],
    tenure_risk_breakdown: [],
    satisfaction_vs_churn_risk: [],
    engagement_by_risk: [
      { risk_category: 'Low', avg_usage_hours: 20, avg_support_interactions: 0, avg_app_switches: 1 },
      { risk_category: 'High', avg_usage_hours: 5, avg_support_interactions: 5, avg_app_switches: 10 }
    ],
    recommendation_type_counts: [],
    tables: {
      top_high_risk_customers: [
        { customer_id: 'CUST-1', churn_probability: 95.0, tenure_months: 2, customer_support_interactions: 5, recommendation_type: 'Offer Discount' }
      ],
      low_engagement_high_risk_customers: [],
      top_revenue_at_risk_customers: []
    }
  };

  const mockResults = {
    total: 2,
    results: [
      {
        customer_id: 'CUST-1',
        age: 30,
        income_level: 'Medium',
        number_of_subscriptions: 1,
        tenure_months: 2,
        monthly_total_spend: 120.0,
        avg_usage_hours_per_week: 5.0,
        app_switch_frequency: 10,
        customer_support_interactions: 5,
        satisfaction_score: 2,
        discount_used: false,
        device_type: 'Android',
        payment_mode: 'UPI',
        churn_probability: 95.0,
        probability_confidence_lower: 90.0,
        probability_confidence_upper: 100.0,
        risk_category: 'High',
        will_cancel: 1,
        recommendation_type: 'Offer Discount',
        recommendation_desc: 'Apply discount',
        predicted_at: '2026-07-13T14:32:00Z',
        model_version: 'v1.2.0-catboost'
      }
    ]
  };

  beforeEach(() => {
    jest.clearAllMocks();
    api.getBulkJobInsights.mockResolvedValue(mockInsights);
    api.getBulkJobResults.mockResolvedValue(mockResults);
  });

  it('renders insights title and KPI values after loading', async () => {
    render(
      <DatasetInsights
        jobId="test-job-id"
        onViewChange={mockViewChange}
        setSelectedJobId={mockSetSelectedJobId}
        onNotify={mockNotify}
      />
    );

    expect(screen.getByText(/Generating Dataset Insights Report.../i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Dataset Insights Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Total Monitored')).toBeInTheDocument();
    expect(screen.getByText('Predicted Churn')).toBeInTheDocument();
    expect(screen.getByText('$120')).toBeInTheDocument(); // revenue at risk
  });

  it('navigates back to dashboard when back button is clicked', async () => {
    render(
      <DatasetInsights
        jobId="test-job-id"
        onViewChange={mockViewChange}
        setSelectedJobId={mockSetSelectedJobId}
        onNotify={mockNotify}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Back to Executive Dashboard/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Back to Executive Dashboard/i }));

    expect(mockSetSelectedJobId).toHaveBeenCalledWith('');
    expect(mockViewChange).toHaveBeenCalledWith('dashboard');
  });

  it('triggers CSV download on button click', async () => {
    api.exportReport.mockResolvedValue({ blob: new Blob(), filename: 'report.csv' });
    
    render(
      <DatasetInsights
        jobId="test-job-id"
        onViewChange={mockViewChange}
        setSelectedJobId={mockSetSelectedJobId}
        onNotify={mockNotify}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Download Results CSV/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Download Results CSV/i }));

    await waitFor(() => {
      expect(api.exportReport).toHaveBeenCalledWith('csv', { jobId: 'test-job-id' });
    });
  });

  it('triggers PDF download on button click', async () => {
    api.exportBulkPdfReport.mockResolvedValue({ blob: new Blob(), filename: 'report.pdf' });
    
    render(
      <DatasetInsights
        jobId="test-job-id"
        onViewChange={mockViewChange}
        setSelectedJobId={mockSetSelectedJobId}
        onNotify={mockNotify}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Download Insights PDF/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Download Insights PDF/i }));

    await waitFor(() => {
      expect(api.exportBulkPdfReport).toHaveBeenCalledWith('test-job-id');
    });
  });
});
