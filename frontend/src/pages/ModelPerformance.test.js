import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ModelPerformance from './ModelPerformance';

describe('ModelPerformance', () => {
  beforeEach(() => {
    global.fetch = jest.fn((url) => {
      if (url.includes('/model/metrics')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
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
          })
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
      expect(screen.getByText('v1.2.0-catboost-test')).toBeInTheDocument();
    });

    // Check performance metrics
    expect(screen.getByText('85.00%')).toBeInTheDocument(); // Accuracy
    expect(screen.getByText('83.00%')).toBeInTheDocument(); // Precision
    expect(screen.getByText('81.00%')).toBeInTheDocument(); // Recall
    expect(screen.getByText('82.00%')).toBeInTheDocument(); // F1 Score
    expect(screen.getByText('89.00%')).toBeInTheDocument(); // ROC-AUC
    
    // Check confusion matrix values
    expect(screen.getByText('800')).toBeInTheDocument(); // TN
    expect(screen.getByText('20')).toBeInTheDocument(); // FP
    expect(screen.getByText('80')).toBeInTheDocument(); // FN
    expect(screen.getByText('100')).toBeInTheDocument(); // TP

    // Check feature importance elements
    expect(screen.getByText('Tenure Months')).toBeInTheDocument();
    expect(screen.getByText('Satisfaction Score')).toBeInTheDocument();
    expect(screen.getByText('Customer Support Interactions')).toBeInTheDocument();
  });
});
