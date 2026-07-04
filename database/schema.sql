-- database/schema.sql

-- 1. Customers Table (Core Demographics)
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    age INT NOT NULL,
    income_level VARCHAR(10) NOT NULL CHECK (income_level IN ('Low', 'Medium', 'High')),
    device_type VARCHAR(20) NOT NULL CHECK (device_type IN ('Android', 'iOS', 'Web')),
    payment_mode VARCHAR(20) NOT NULL CHECK (payment_mode IN ('Credit Card', 'UPI', 'Debit Card', 'Wallet'))
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
    satisfaction_score INT NOT NULL CHECK (satisfaction_score BETWEEN 1 AND 10)
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
-- Database Schema - Administrator User Setup

-- Automatically update updated_at timestamp helper
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Admin Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Trigger assignment for updated_at tracking
DROP TRIGGER IF EXISTS set_timestamp ON users;
CREATE TRIGGER set_timestamp
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();
