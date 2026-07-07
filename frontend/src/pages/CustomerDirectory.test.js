import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import CustomerDirectory from './CustomerDirectory';
import * as apiService from '../services/api';

jest.mock('../services/api');

const customerResponse = {
  total: 1,
  page: 1,
  limit: 20,
  results: [
    {
      customer_id: 'CUST0001',
      age: 34,
      income_level: 'Medium',
      tenure_months: 8,
      monthly_total_spend: 79.5,
      satisfaction_score: 2,
      device_type: 'Android',
      payment_mode: 'UPI',
      churn_probability: 89,
      risk_category: 'High',
      will_cancel: 1,
      recommendation_type: 'Offer Discount'
    }
  ]
};

describe('CustomerDirectory', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    apiService.getCustomers.mockResolvedValue(customerResponse);
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it('loads customers and displays the matched record count', async () => {
    render(<CustomerDirectory onViewChange={jest.fn()} onSelectCustomer={jest.fn()} />);

    expect(await screen.findByText('CUST0001')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(apiService.getCustomers).toHaveBeenCalledWith(1, 20, {
      searchId: '',
      willCancel: null,
      riskCategories: [],
      incomeLevels: [],
      deviceTypes: [],
      paymentModes: []
    });
  });

  it('debounces ID search and sends selected filters', async () => {
    render(<CustomerDirectory onViewChange={jest.fn()} onSelectCustomer={jest.fn()} />);
    await screen.findByText('CUST0001');

    fireEvent.change(screen.getByPlaceholderText(/C10239/i), { target: { value: ' CUST ' } });
    fireEvent.click(screen.getAllByLabelText('High')[0]);
    fireEvent.click(screen.getByLabelText('iOS'));
    fireEvent.click(screen.getByLabelText('Wallet'));
    fireEvent.click(screen.getByLabelText('Predicted Churn'));

    await act(async () => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(apiService.getCustomers).toHaveBeenLastCalledWith(1, 20, {
        searchId: 'CUST',
        willCancel: 1,
        riskCategories: ['High'],
        incomeLevels: [],
        deviceTypes: ['iOS'],
        paymentModes: ['Wallet']
      });
    });
  });
});
