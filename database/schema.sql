-- database/schema.sql

-- 1. Customers Table (Core Demographics)
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    age INT NOT NULL,
    income_level VARCHAR(10) NOT NULL CHECK (income_level IN ('Low', 'Medium', 'High')),
    device_type VARCHAR(20) NOT NULL CHECK (device_type IN ('Mobile', 'Smart TV', 'Desktop', 'Tablet')),
    payment_mode VARCHAR(20) NOT NULL CHECK (payment_mode IN ('Credit Card', 'UPI', 'Debit Card', 'Net Banking'))
);

-- 2. Customer Subscriptions Table
CREATE TABLE IF NOT EXISTS customer_subscriptions (
    customer_id VARCHAR(50) PRIMARY KEY REFERENCES customers(customer_id) ON DELETE CASCADE,
    number_of_subscriptions INT NOT NULL DEFAULT 1,
    tenure_months INT NOT NULL,
    monthly_total_spend NUMERIC(10, 2) NOT NULL,
    discount_used BOOLEAN NOT NULL DEFAULT FALSE,
    will_cancel_next_3_months INT DEFAULT NULL
);

-- 3. Customer Behavior Table
CREATE TABLE IF NOT EXISTS customer_behavior (
    customer_id VARCHAR(50) PRIMARY KEY REFERENCES customers(customer_id) ON DELETE CASCADE,
    avg_usage_hours_per_week NUMERIC(5, 2) NOT NULL,
    app_switch_frequency INT NOT NULL,
    customer_support_interactions INT NOT NULL DEFAULT 0,
    satisfaction_score INT NOT NULL CHECK (satisfaction_score BETWEEN 1 AND 5)
);

-- 4. Prediction History Table (REQUIRED SCHEMA)
-- Keeps track of every prediction run over time so we can see if risk increases or decreases
CREATE TABLE IF NOT EXISTS prediction_history (
    history_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    risk_score NUMERIC(5, 2) NOT NULL,            -- e.g., 84.50 (for 0-100%)
    risk_category VARCHAR(20) NOT NULL,           -- 'VERY_LOW', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    prediction_result INT NOT NULL,               -- 1 = Likely to Cancel, 0 = Not Likely to Cancel
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);