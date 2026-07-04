-- ==========================================
-- PostgreSQL Schema & Analytics Queries
-- Subscription Cancellation Prediction System
-- Bootcamp by ACE students Team 3
-- ==========================================

-- ==========================================
-- Part 1: Database DDL (Schema Definition)
-- ==========================================

-- Drop tables if they exist (for easy setup)
DROP VIEW IF EXISTS v_customer_predictions CASCADE;
DROP TABLE IF EXISTS churn_predictions CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS model_metrics CASCADE;

-- 1. Customers Table: Stores customer profile details and usage attributes
CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    age INT NOT NULL CHECK (age >= 18 AND age <= 120),
    income_level VARCHAR(10) NOT NULL CHECK (income_level IN ('Low', 'Medium', 'High')),
    number_of_subscriptions INT NOT NULL DEFAULT 1 CHECK (number_of_subscriptions >= 0),
    tenure_months INT NOT NULL CHECK (tenure_months >= 0),
    monthly_total_spend NUMERIC(10, 2) NOT NULL CHECK (monthly_total_spend >= 0.00),
    avg_usage_hours_per_week NUMERIC(5, 2) NOT NULL CHECK (avg_usage_hours_per_week >= 0.00),
    app_switch_frequency VARCHAR(10) NOT NULL CHECK (app_switch_frequency IN ('Low', 'Medium', 'High')),
    customer_support_interactions INT NOT NULL DEFAULT 0 CHECK (customer_support_interactions >= 0),
    satisfaction_score INT NOT NULL CHECK (satisfaction_score BETWEEN 1 AND 5),
    discount_used BOOLEAN NOT NULL DEFAULT FALSE,
    device_type VARCHAR(20) NOT NULL CHECK (device_type IN ('Mobile', 'Tablet', 'Desktop', 'Smart TV')),
    payment_mode VARCHAR(30) NOT NULL CHECK (payment_mode IN ('Credit Card', 'Debit Card', 'Net Banking', 'UPI', 'Digital Wallet')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. Churn Predictions Table: Stores churn prediction outputs for each customer
CREATE TABLE churn_predictions (
    prediction_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    churn_probability NUMERIC(5, 2) NOT NULL CHECK (churn_probability BETWEEN 0.00 AND 100.00),
    risk_category VARCHAR(10) NOT NULL CHECK (risk_category IN ('Low', 'Medium', 'High')),
    will_cancel INT NOT NULL CHECK (will_cancel IN (0, 1)),
    explainability_json JSONB, -- Stores SHAP values and key contributing factors
    recommendation_type VARCHAR(50) NOT NULL CHECK (recommendation_type IN ('Offer Discount', 'Provide Free Trial', 'Contact Customer Support', 'Subscription Upgrade', 'Provide Personalized Offers', 'No Action Required')),
    recommendation_desc TEXT NOT NULL,
    predicted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. Model Metrics Table: Tracks machine learning model evaluations over time
CREATE TABLE model_metrics (
    metric_id SERIAL PRIMARY KEY,
    model_version VARCHAR(20) NOT NULL,
    accuracy NUMERIC(5, 4) NOT NULL CHECK (accuracy BETWEEN 0.0000 AND 1.0000),
    precision NUMERIC(5, 4) NOT NULL CHECK (precision BETWEEN 0.0000 AND 1.0000),
    recall NUMERIC(5, 4) NOT NULL CHECK (recall BETWEEN 0.0000 AND 1.0000),
    f1_score NUMERIC(5, 4) NOT NULL CHECK (f1_score BETWEEN 0.0000 AND 1.0000),
    roc_auc NUMERIC(5, 4) NOT NULL CHECK (roc_auc BETWEEN 0.0000 AND 1.0000),
    confusion_matrix JSONB NOT NULL, -- e.g., {"tp": 1200, "fp": 150, "tn": 13500, "fn": 1096}
    feature_importance JSONB NOT NULL, -- Key-value pairs of features and their importance weights
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ==========================================
-- Part 2: Database Indexes (Performance Optimization)
-- ==========================================

-- Index on frequently queried columns in Customers
CREATE INDEX idx_customers_demographics ON customers(income_level, device_type, payment_mode);
CREATE INDEX idx_customers_satisfaction ON customers(satisfaction_score);
CREATE INDEX idx_customers_lower_customer_id ON customers(LOWER(customer_id));

-- Indexes on Churn Predictions for faster lookups, sorting and filtering
CREATE INDEX idx_predictions_customer_id ON churn_predictions(customer_id);
CREATE INDEX idx_predictions_customer_predicted_at ON churn_predictions(customer_id, predicted_at DESC);
CREATE INDEX idx_predictions_score ON churn_predictions(churn_probability DESC);
CREATE INDEX idx_predictions_risk ON churn_predictions(risk_category);
CREATE INDEX idx_predictions_risk_will ON churn_predictions(risk_category, will_cancel);
CREATE INDEX idx_predictions_predicted_at ON churn_predictions(predicted_at DESC);

-- ==========================================
-- Part 3: Database View (Latest Predictions)
-- ==========================================

-- View to get the latest prediction for every customer
CREATE OR REPLACE VIEW v_customer_predictions AS
SELECT DISTINCT ON (c.customer_id)
    c.customer_id,
    c.age,
    c.income_level,
    c.number_of_subscriptions,
    c.tenure_months,
    c.monthly_total_spend,
    c.avg_usage_hours_per_week,
    c.app_switch_frequency,
    c.customer_support_interactions,
    c.satisfaction_score,
    c.discount_used,
    c.device_type,
    c.payment_mode,
    p.prediction_id,
    p.churn_probability,
    p.risk_category,
    p.will_cancel,
    p.explainability_json,
    p.recommendation_type,
    p.recommendation_desc,
    p.predicted_at
FROM customers c
LEFT JOIN churn_predictions p ON c.customer_id = p.customer_id
ORDER BY c.customer_id, p.predicted_at DESC;


-- ==========================================
-- Part 4: Executive Dashboard queries (KPIs)
-- ==========================================

-- Query: Dashboard KPIs Summary
-- Retrieves: Total Customers, Predicted Churn, High Risk, Avg Risk, Avg Satisfaction, Avg Monthly Spend, Avg Tenure
SELECT 
    COUNT(customer_id) AS total_customers,
    COUNT(CASE WHEN will_cancel = 1 THEN 1 END) AS predicted_churn_customers,
    COUNT(CASE WHEN risk_category = 'High' THEN 1 END) AS high_risk_customers,
    ROUND(AVG(churn_probability), 2) AS average_churn_risk,
    ROUND(AVG(satisfaction_score), 2) AS average_satisfaction,
    ROUND(AVG(monthly_total_spend), 2) AS average_monthly_spend,
    ROUND(AVG(tenure_months), 1) AS average_tenure_months,
    ROUND(SUM(CASE WHEN will_cancel = 1 THEN monthly_total_spend ELSE 0 END), 2) AS monthly_revenue_at_risk
FROM v_customer_predictions;


-- ==========================================
-- Part 5: Analytics Dashboard Queries (Visualizations)
-- ==========================================

-- Query 1: Churn Risk Category Distribution
SELECT 
    risk_category,
    COUNT(*) AS customer_count,
    ROUND((COUNT(*) * 100.0) / SUM(COUNT(*)) OVER(), 2) AS percentage
FROM v_customer_predictions
GROUP BY risk_category
ORDER BY 
    CASE risk_category 
        WHEN 'Low' THEN 1 
        WHEN 'Medium' THEN 2 
        WHEN 'High' THEN 3 
    END;

-- Query 2: Churn Rate by Income Level
SELECT 
    income_level,
    COUNT(*) AS total_customers,
    COUNT(CASE WHEN will_cancel = 1 THEN 1 END) AS churn_customers,
    ROUND((COUNT(CASE WHEN will_cancel = 1 THEN 1 END) * 100.0) / COUNT(*), 2) AS churn_rate
FROM v_customer_predictions
GROUP BY income_level
ORDER BY 
    CASE income_level 
        WHEN 'Low' THEN 1 
        WHEN 'Medium' THEN 2 
        WHEN 'High' THEN 3 
    END;

-- Query 3: Churn Rate & Customer Count by Device Type
SELECT 
    device_type,
    COUNT(*) AS total_customers,
    COUNT(CASE WHEN will_cancel = 1 THEN 1 END) AS churn_customers,
    ROUND((COUNT(CASE WHEN will_cancel = 1 THEN 1 END) * 100.0) / COUNT(*), 2) AS churn_rate
FROM v_customer_predictions
GROUP BY device_type
ORDER BY churn_rate DESC;

-- Query 4: Churn Rate & Customer Count by Payment Mode
SELECT 
    payment_mode,
    COUNT(*) AS total_customers,
    COUNT(CASE WHEN will_cancel = 1 THEN 1 END) AS churn_customers,
    ROUND((COUNT(CASE WHEN will_cancel = 1 THEN 1 END) * 100.0) / COUNT(*), 2) AS churn_rate
FROM v_customer_predictions
GROUP BY payment_mode
ORDER BY churn_rate DESC;

-- Query 5: Spend buckets and Churn correlation
SELECT 
    spend_bucket,
    COUNT(*) AS total_customers,
    COUNT(CASE WHEN will_cancel = 1 THEN 1 END) AS churn_customers,
    ROUND((COUNT(CASE WHEN will_cancel = 1 THEN 1 END) * 100.0) / COUNT(*), 2) AS churn_rate
FROM (
    SELECT 
        will_cancel,
        CASE 
            WHEN monthly_total_spend < 20 THEN 'Under $20'
            WHEN monthly_total_spend BETWEEN 20 AND 50 THEN '$20 - $50'
            WHEN monthly_total_spend BETWEEN 51 AND 100 THEN '$51 - $100'
            ELSE 'Over $100'
        END AS spend_bucket
    FROM v_customer_predictions
) sub
GROUP BY spend_bucket
ORDER BY MIN(spend_bucket);

-- Query 6: Customer Tenure vs. Churn Rate
SELECT 
    tenure_bucket,
    COUNT(*) AS total_customers,
    COUNT(CASE WHEN will_cancel = 1 THEN 1 END) AS churn_customers,
    ROUND((COUNT(CASE WHEN will_cancel = 1 THEN 1 END) * 100.0) / COUNT(*), 2) AS churn_rate
FROM (
    SELECT 
        will_cancel,
        CASE 
            WHEN tenure_months <= 3 THEN '0-3 Months (New)'
            WHEN tenure_months BETWEEN 4 AND 6 THEN '4-6 Months'
            WHEN tenure_months BETWEEN 7 AND 12 THEN '7-12 Months'
            ELSE '12+ Months (Loyal)'
        END AS tenure_bucket
    FROM v_customer_predictions
) sub
GROUP BY tenure_bucket
ORDER BY 
    CASE tenure_bucket 
        WHEN '0-3 Months (New)' THEN 1 
        WHEN '4-6 Months' THEN 2 
        WHEN '7-12 Months' THEN 3 
        WHEN '12+ Months (Loyal)' THEN 4 
    END;

-- Query 7: Customer Satisfaction vs. Churn Rate & Avg Interactions
SELECT 
    satisfaction_score,
    COUNT(*) AS total_customers,
    COUNT(CASE WHEN will_cancel = 1 THEN 1 END) AS churn_customers,
    ROUND((COUNT(CASE WHEN will_cancel = 1 THEN 1 END) * 100.0) / COUNT(*), 2) AS churn_rate,
    ROUND(AVG(customer_support_interactions), 2) AS avg_support_interactions
FROM v_customer_predictions
GROUP BY satisfaction_score
ORDER BY satisfaction_score DESC;

-- Query 8: Behavioral Churn Matrix (Spend vs. Engagement/Usage Hours)
-- Segments customers based on Spend and Usage Hours to identify "At Risk" profiles
SELECT 
    spend_profile,
    usage_profile,
    COUNT(*) AS total_customers,
    COUNT(CASE WHEN will_cancel = 1 THEN 1 END) AS churn_customers,
    ROUND((COUNT(CASE WHEN will_cancel = 1 THEN 1 END) * 100.0) / COUNT(*), 2) AS churn_rate
FROM (
    SELECT 
        will_cancel,
        CASE WHEN monthly_total_spend >= 60 THEN 'High Spender' ELSE 'Value Spender' END AS spend_profile,
        CASE WHEN avg_usage_hours_per_week >= 15 THEN 'High Usage' ELSE 'Low Usage' END AS usage_profile
    FROM v_customer_predictions
) sub
GROUP BY spend_profile, usage_profile
ORDER BY churn_rate DESC;


-- ==========================================
-- Part 6: Customer Segmentation Overview
-- ==========================================

-- Query: Customer Segments and their Churn Statistics
-- Segment definitions:
-- - High Risk Customers: Churn probability >= 70%
-- - Loyal Customers: Tenure > 12 months AND churn probability < 30%
-- - Premium Customers: Monthly spend >= 80 AND satisfaction_score >= 4
-- - Budget Customers: Monthly spend < 30
WITH segmented_customers AS (
    SELECT 
        customer_id,
        churn_probability,
        tenure_months,
        monthly_total_spend,
        satisfaction_score,
        CASE 
            WHEN churn_probability >= 70 THEN 'High Risk'
            WHEN tenure_months > 12 AND churn_probability < 30 THEN 'Loyal'
            WHEN monthly_total_spend >= 80 AND satisfaction_score >= 4 THEN 'Premium'
            WHEN monthly_total_spend < 30 THEN 'Budget'
            ELSE 'Standard'
        END AS segment
    FROM v_customer_predictions
)
SELECT 
    segment,
    COUNT(*) AS customer_count,
    ROUND((COUNT(*) * 100.0) / SUM(COUNT(*)) OVER(), 2) AS percentage,
    ROUND(AVG(churn_probability), 2) AS average_churn_risk
FROM segmented_customers
GROUP BY segment
ORDER BY average_churn_risk DESC;


-- ==========================================
-- Part 7: Customer Search, Filters & Directory
-- ==========================================

-- Query: Paginated Customer Directory with Multi-Filters
-- Note: Replace placeholders with programming variables (e.g., :search_id, :income, :device, :payment, :risk, :limit, :offset)
-- The structure shows how multi-select filter arrays can be checked in Postgres.
SELECT 
    customer_id,
    age,
    income_level,
    tenure_months,
    monthly_total_spend,
    satisfaction_score,
    device_type,
    payment_mode,
    churn_probability,
    risk_category,
    will_cancel,
    recommendation_type
FROM v_customer_predictions
WHERE 
    -- Search filter (prefix matching)
    (customer_id ILIKE '%' || :search_id || '%' OR :search_id IS NULL OR :search_id = '')
    -- Multi-select filters
    AND (income_level = ANY(:income_levels) OR :income_levels IS NULL)
    AND (device_type = ANY(:device_types) OR :device_types IS NULL)
    AND (payment_mode = ANY(:payment_modes) OR :payment_modes IS NULL)
    AND (risk_category = ANY(:risk_categories) OR :risk_categories IS NULL)
    AND (will_cancel = :will_cancel OR :will_cancel IS NULL)
ORDER BY churn_probability DESC
LIMIT :limit OFFSET :offset;


-- ==========================================
-- Part 8: Report Generation & Exports
-- ==========================================

-- Query 1: High-Risk Customer Escalation Report (Ready for CSV/Excel/PDF download)
-- Selects top customers who are likely to cancel and lists the recommended action
SELECT 
    customer_id AS "Customer ID",
    age AS "Age",
    tenure_months AS "Tenure (Months)",
    monthly_total_spend AS "Monthly Spend ($)",
    avg_usage_hours_per_week AS "Weekly Usage (Hrs)",
    customer_support_interactions AS "Support Tickets",
    satisfaction_score AS "Satisfaction (1-5)",
    ROUND(churn_probability, 1) || '%' AS "Churn Probability",
    risk_category AS "Risk Category",
    recommendation_type AS "Recommended Offer",
    recommendation_desc AS "Action Description"
FROM v_customer_predictions
WHERE risk_category = 'High'
ORDER BY churn_probability DESC;

-- Query 2: Summary Metrics by Recommendation Actions
-- Helps Customer Success Teams budget retention offers (e.g. Total discount cost)
SELECT 
    recommendation_type,
    COUNT(*) AS eligible_customers,
    ROUND(AVG(churn_probability), 2) AS average_churn_probability,
    SUM(monthly_total_spend) AS monthly_value_affected,
    -- Estimating monthly discount cost if we give 20% discount on their current spend
    ROUND(SUM(CASE WHEN recommendation_type = 'Offer Discount' THEN monthly_total_spend * 0.20 ELSE 0 END), 2) AS estimated_monthly_discount_cost
FROM v_customer_predictions
GROUP BY recommendation_type
ORDER BY eligible_customers DESC;


-- ==========================================
-- Part 9: Single Customer Detailed Insights
-- ==========================================

-- Query 1: Retrieve Full Customer Details and Churn Metrics
SELECT * 
FROM v_customer_predictions 
WHERE customer_id = :customer_id;

-- Query 2: Retrieve Historical Predictions for Trend Analysis (Single Customer)
SELECT 
    prediction_id,
    churn_probability,
    risk_category,
    will_cancel,
    recommendation_type,
    predicted_at
FROM churn_predictions
WHERE customer_id = :customer_id
ORDER BY predicted_at DESC;
