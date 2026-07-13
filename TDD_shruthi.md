# Churn Prediction System: Test-Driven Development (TDD) for Data Preprocessing

**Author:** Shruthi  
**Date:** July 13, 2026  
**Scope:** Data Preprocessing Pipeline Validation & Robustness Test-Driven Development

---

## 1. Executive Summary

This document outlines the Test-Driven Development (TDD) and unit testing implemented for the **Data Preprocessing Pipeline** of the Subscription Cancellation Prediction System. 

Under the design specifications of **Shruthi**, a complete unit testing framework was created from scratch for [preprocessing.py](file:///c:/Users/shrut/Downloads/team_3/bootcamp-ace-26-team-3/backend/app/core/preprocessing.py) to guarantee:
- Robust error handling for unfitted pipelines.
- Accurate and consistent calculation of engineered features.
- Fail-safe default mapping values for missing input fields.
- Robust imputation and standard scaling of numerical features.
- Mathematical consistency between `fit_transform()` and individual `fit()` -> `transform()` calls.

---

## 2. Test Suite Architecture

The preprocessing TDD test suite is added under the `backend/tests/` directory:

```text
backend/tests/
├── ...
└── test_preprocessing.py        # [NEW] Preprocessing pipeline validation & edge cases
```

---

## 3. TDD Preprocessing Pipeline Overview

The preprocessor `SubscriptionPreprocessor` prepares raw client datasets of 14 features for ML binary classification. Key TDD goals validated include:

### 3.1 Engineered Features
To capture complex non-linear behaviors, the pipeline engineers 5 columns. Calculations tested:
* **Spend_Per_Subscription**: $\text{Monthly\_Total\_Spend} / (\text{Number\_of\_Subscriptions} + 10^{-5})$
* **Usage_Per_Subscription**: $\text{Avg\_Usage\_Hours\_Per\_Week} / (\text{Number\_of\_Subscriptions} + 10^{-5})$
* **Interactions_Per_Tenure_Month**: $\text{Customer\_Support\_Interactions} / (\text{Tenure\_Months} + 10^{-5})$
* **Engagement_Score**: $\text{Avg\_Usage\_Hours\_Per\_Week} \times \text{Satisfaction\_Score}$
* **Risk_Indicator**: $\text{Customer\_Support\_Interactions} \times (10.0 - \text{Satisfaction\_Score})$

### 3.2 Robust Fallbacks (Missing Data)
Tested imputer rules for missing fields in production:
* **Numerical Features**: Imputed using the `median` value fit from training data.
* **Income_Level**: Maps Low $\rightarrow 1$, Medium $\rightarrow 2$, High $\rightarrow 3$ (defaults to $2$ / Medium if missing).
* **Discount_Used**: Binary flag (defaults to $0$ if missing).
* **Satisfaction_Score**: Pass-through index (defaults to $3$ / neutral if missing).

---

## 4. Test Specifications (`test_preprocessing.py`)

Detailed descriptions of the implemented test cases:

1. **`test_unfitted_transform_raises_value_error`**
   - **TDD Objective**: Verify that invoking `.transform()` before `.fit()` is executed raises a `ValueError` with the message `"Preprocessor has not been fitted yet!"`.

2. **`test_feature_engineering_calculations`**
   - **TDD Objective**: Supply specific inputs to verify that each engineered mathematical formula calculates the expected output.
   - **Boundary Safety**: Validates boundary conditions (e.g., $0$ subscriptions/tenure months) to verify that the epsilon value (`1e-5`) successfully prevents division-by-zero errors.

3. **`test_income_and_discount_mappings`**
   - **TDD Objective**: Validate categorical ordinal mapping rules. Asserts that missing values (`None` / `NaN`) default gracefully to the specified fallbacks (`Income_Level` $\rightarrow 2$, `Satisfaction_Score` $\rightarrow 3$, `Discount_Used` $\rightarrow 0$).

4. **`test_imputation_and_scaling`**
   - **TDD Objective**: Ensure that columns containing missing values undergo median imputation based on the fitted training set and are scaled correctly via `StandardScaler`.

5. **`test_fit_transform_consistency`**
   - **TDD Objective**: Confirm that the combined pipeline `.fit_transform(df)` yields identical dataframes to the sequential execution of `.fit(df)` followed by `.transform(df)`.

---

## 5. Execution Guide

To execute the data preprocessing test suite, ensure the virtual environment is active, then run:

```powershell
# Run the preprocessing test suite specifically
.venv\Scripts\python.exe -m pytest backend/tests/test_preprocessing.py -v
```

### Verification Result:
```text
collected 5 items

backend/tests/test_preprocessing.py::test_unfitted_transform_raises_value_error PASSED   [ 20%]
backend/tests/test_preprocessing.py::test_feature_engineering_calculations PASSED        [ 40%]
backend/tests/test_preprocessing.py::test_income_and_discount_mappings PASSED            [ 60%]
backend/tests/test_preprocessing.py::test_imputation_and_scaling PASSED                  [ 80%]
backend/tests/test_preprocessing.py::test_fit_transform_consistency PASSED               [100%]

======================== 5 passed, 1 warning in 2.08s =========================
```

---
*Document maintained by Shruthi.*
