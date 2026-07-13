import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import CustomerProfile from './CustomerProfile';
import * as apiService from '../services/api';

jest.mock('../services/api');

const mockProfile = {
  customer_id: '12345',
  age: 34,
  income_level: 'Medium',
  number_of_subscriptions: 2,
  tenure_months: 8,
  monthly_total_spend: 79.50,
  avg_usage_hours_per_week: 15.0,
  app_switch_frequency: 5,
  customer_support_interactions: 2,
  satisfaction_score: 6,
  discount_used: false,
  device_type: 'Android',
  payment_mode: 'UPI',
  created_at: '2026-07-06T05:49:36Z',
  churn_probability: 45.5,
  probability_confidence_lower: 40.5,
  probability_confidence_upper: 50.5,
  risk_category: 'Medium',
  will_cancel: 1,
  explainability: { age: 0.1, tenure_months: -0.2 },
  recommendation_type: 'Proactive Engagement Plan',
  recommendation_desc: 'Why this customer is at risk: Customer showing moderate churn signs.\nRecommended action: Trigger usage campaign.\nPriority: Medium (Proactive)\nExpected impact: Increases product adoption.\nNext step: Monitor metrics'
};

describe('CustomerProfile', () => {
  beforeEach(() => {
    apiService.getCustomerProfile.mockResolvedValue(mockProfile);
    apiService.getCustomerPredictionHistory.mockResolvedValue([]);
    apiService.runSinglePrediction.mockResolvedValue({
      ...mockProfile,
      churn_probability: 48.0,
      risk_category: 'Medium'
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders customer profile and shows exactly one Retention Recommendation heading', async () => {
    render(<CustomerProfile selectedCustomerId="12345" onPredictionRecalculated={jest.fn()} />);

    expect((await screen.findAllByText('12345')).length).toBeGreaterThanOrEqual(1);


    const headings = screen.getAllByText(/Retention Recommendation/i);
    expect(headings.length).toBe(1);

    expect(screen.getByText('Why this customer is at risk')).toBeInTheDocument();
    expect(screen.getByText('Customer showing moderate churn signs.')).toBeInTheDocument();
    expect(screen.getByText('Recommended action')).toBeInTheDocument();
    expect(screen.getByText('Trigger usage campaign.')).toBeInTheDocument();
    expect(screen.getByText('Next action step')).toBeInTheDocument();
  });

  it('allows calculating predictions via the unified Calculate Prediction button click', async () => {
    const onRecalcMock = jest.fn();
    render(<CustomerProfile selectedCustomerId="12345" onPredictionRecalculated={onRecalcMock} />);

    expect((await screen.findAllByText('12345')).length).toBeGreaterThanOrEqual(1);

    // Confirm that old button labels are not present
    expect(screen.queryByText('Generate Model Prediction')).not.toBeInTheDocument();
    expect(screen.queryByText('Recalculate Prediction')).not.toBeInTheDocument();

    // Confirm that "Calculate Prediction" is visible
    const calcBtn = screen.getByRole('button', { name: /Calculate Prediction/i });
    expect(calcBtn).toBeInTheDocument();

    // Trigger calculation
    fireEvent.click(calcBtn);

    await waitFor(() => {
      expect(apiService.runSinglePrediction).toHaveBeenCalledTimes(1);
      expect(apiService.runSinglePrediction).toHaveBeenCalledWith('12345');
      expect(onRecalcMock).toHaveBeenCalled();
    });
  });
});
