# Churn Prediction System: Test-Driven Development (TDD) & Unit Testing Documentation

**Author:** Manthena Sri Harshitha (Team Lead)  
**Date:** July 10, 2026  
**Scope:** Backend FastAPI Unit Testing & Diagnostics TDD

---

## 1. Executive Summary

This documentation outlines the unit testing architecture and Test-Driven Development (TDD) methodology implemented for the FastAPI backend of the Subscription Cancellation Prediction System. 

Under the leadership of **Manthena Sri Harshitha**, a robust testing framework has been established. The existing test suite was debugged to ensure a 100% pass rate, and a new suite of 16 comprehensive unit tests was developed from scratch using TDD for the Model Performance and A/B Testing diagnostic endpoints.

---

## 2. Test Suite Architecture

The tests are organized under the `backend/tests/` directory and leverage the `pytest` testing framework alongside asynchronous testing plugins.

```text
backend/tests/
├── test_bulk_predictions.py            # Bulk prediction async pipelines & file exports
├── test_model_performance.py           # [NEW] Model metrics, deployments, & A/B testing
├── test_probability_implementation.py  # Churn probability & confidence bounds
└── test_shap_explainability.py        # Local SHAP calculations & features mapping
```

---

## 3. Major Debugging & Refactoring

### Bulk Prediction Property Mocking Fix
**Problem:** The test `test_process_bulk_predictions_task_writes_real_results` in `test_bulk_predictions.py` was failing with:
`AttributeError: property 'is_ready' of 'ModelService' object has no setter`
This occurred because the test attempted to monkeypatch the read-only class property `is_ready` directly on the `model_service` instance.

**Solution:** **Manthena Sri Harshitha** resolved this issue by intercepting the property definition at the class descriptor level (`predictions.model_service.__class__`):
```python
monkeypatch.setattr(predictions.model_service.__class__, "is_ready", property(lambda self: False))
```
This successfully restored the test suite to a fully operational, passing state.

---

## 4. Test-Driven Development: Model Diagnostics (`model.py`)

Using TDD principles, the test specifications for the Model Performance router [model.py](file:///d:/Team-3/backend/app/routers/model.py) were created and implemented in [test_model_performance.py](file:///d:/Team-3/backend/tests/test_model_performance.py).

### Coverage Details:

1. **Model Metrics Retrieval (`GET /model/metrics`)**
   - **Database Retrieval Success**: Mocks SQLAlchemy session executes to return a valid metrics database record. Asserts correct data formats, types, and values.
   - **Database Fallback to JSON**: Mocks a database failure and asserts that the router successfully falls back to reading metrics from local `model_metrics.json`.
   - **Full Fallback**: Mocks failures of both the database and file systems, asserting that the endpoint safely falls back to standard hardcoded metrics without crashing.

2. **Zero-Downtime Deployment (`POST /model/deploy/{model_version}`)**
   - **Security Role Restrictions**: Verifies standard users receive `403 Forbidden` responses.
   - **Successful Deployment**: Verifies that admin requests successfully trigger a background deployment task via FastAPI's `BackgroundTasks`.

3. **A/B Testing Lifecycle (`POST /model/ab-test/*`)**
   - **Role Restrictions**: Asserts that only admin users can access start and stop actions.
   - **Readiness Checks**: Returns `503 Service Unavailable` if no champion model is loaded.
   - **Self-Comparison Blocks**: Raises `400 Bad Request` if a challenger is set to the same version as the champion.
   - **Missing Artifact Handling**: Raises `404 Not Found` if the challenger's file artifacts are missing.
   - **Successful Activation/Deactivation**: Verifies state transitions in `model_service.ab_test_config`.

4. **A/B Comparison Statistics (`GET /model/ab-test/results`)**
   - Mocks aggregate query calls to database views, validating calculations for average churn risk, overall prediction count, predicted churn rates, and risk classification counts.

---

## 5. Execution Guide

To execute the test suite, ensure the python virtual environment is active, then run:

```powershell
# Run the entire test suite
.\.venv\Scripts\python.exe -m pytest backend/tests

# Run specifically the newly implemented model performance tests
.\.venv\Scripts\python.exe -m pytest backend/tests/test_model_performance.py -v
```

### Verification Verification:
All 62 unit tests pass successfully.

---
*Document maintained by Manthena Sri Harshitha.*
