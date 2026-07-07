import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ModelPerformance from './ModelPerformance';

const MOCK_METRICS = {
  model_version: 'v1.2.0-catboost-test',
  accuracy: 0.85,
  precision: 0.83,
  recall: 0.81,
  f1_score: 0.82,
  roc_auc: 0.89,
  confusion_matrix: {
    tp: 100,
    fp: 20,
    tn: 800,
    fn: 80
  },
  feature_importance: {
    Tenure_Months: 40.0,
    Satisfaction_Score: 30.0,
    Customer_Support_Interactions: 20.0
  },
  evaluated_at: '2026-07-06T12:00:00Z'
};

describe('ModelPerformance', () => {
  beforeEach(() => {
    global.fetch = jest.fn((url) => {
      if (url.includes('/model/metrics')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => (MOCK_METRICS)
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders model metrics and confusion matrix values correctly after loading', async () => {
    render(<ModelPerformance onViewChange={jest.fn()} onLogout={jest.fn()} />);

    // Check loading state
    expect(screen.getByText(/Loading model performance/i)).toBeInTheDocument();

    // Wait for metrics to load and display
    await waitFor(() => {
      expect(screen.getByText(MOCK_METRICS.model_version)).toBeInTheDocument();
    });

    // Check performance metrics
    expect(screen.getByText(`${(MOCK_METRICS.accuracy * 100).toFixed(2)}%`)).toBeInTheDocument(); // Accuracy
    expect(screen.getByText(`${(MOCK_METRICS.precision * 100).toFixed(2)}%`)).toBeInTheDocument(); // Precision
    expect(screen.getByText(`${(MOCK_METRICS.recall * 100).toFixed(2)}%`)).toBeInTheDocument(); // Recall
    expect(screen.getByText(`${(MOCK_METRICS.f1_score * 100).toFixed(2)}%`)).toBeInTheDocument(); // F1 Score
    expect(screen.getByText(`${(MOCK_METRICS.roc_auc * 100).toFixed(2)}%`)).toBeInTheDocument(); // ROC-AUC
    
    // Check confusion matrix values
    expect(screen.getByText(MOCK_METRICS.confusion_matrix.tn.toString())).toBeInTheDocument(); // TN
    expect(screen.getByText(MOCK_METRICS.confusion_matrix.fp.toString())).toBeInTheDocument(); // FP
    expect(screen.getByText(MOCK_METRICS.confusion_matrix.fn.toString())).toBeInTheDocument(); // FN
    expect(screen.getByText(MOCK_METRICS.confusion_matrix.tp.toString())).toBeInTheDocument(); // TP

    // Check feature importance elements
    expect(screen.getByText(/Tenure Months/i)).toBeInTheDocument();
    expect(screen.getByText(/Satisfaction Score/i)).toBeInTheDocument();
    expect(screen.getByText(/Customer Support Interactions/i)).toBeInTheDocument();
  });

  it('renders an error message when the API call fails', async () => {
    // Override fetch to simulate a network error
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        json: async () => ({ message: 'Internal Server Error' }),
      })
    );

    render(<ModelPerformance onViewChange={jest.fn()} onLogout={jest.fn()} />);

    // Check for the error message to be displayed
    expect(await screen.findByText(/Internal Server Error/i)).toBeInTheDocument();
    expect(screen.queryByText(/Loading model performance/i)).not.toBeInTheDocument();
  });

  it('calls onLogout when the API returns a 401 Unauthorized status', async () => {
    const mockOnLogout = jest.fn();

    // Override fetch to simulate a 401 error
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        status: 401,
        json: async () => ({ message: 'Unauthorized' }),
      })
    );

    render(<ModelPerformance onViewChange={jest.fn()} onLogout={mockOnLogout} />);

    // Wait for the async actions in useEffect to complete
    await waitFor(() => {
      expect(mockOnLogout).toHaveBeenCalledTimes(1);
    });
  });
});
