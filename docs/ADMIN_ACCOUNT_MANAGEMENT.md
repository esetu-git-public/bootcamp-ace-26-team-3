# Administrator Account Management Guide: User-Management Console

This guide explains how to register new Customer Manager accounts under **Option B (Admin-Only Signup)**.

---

## 1. Security Overview
To protect the subscription prediction dashboard, public signup is disabled. 
* Only a logged-in Administrator (`admin`) can create or provision new Customer Manager accounts.
* All signup requests must contain the `Authorization: Bearer <token>` header of an active administrator.

---

## 2. Seeded Default Administrator Credentials
On database initialization, the default administrator is created:
* **Username:** `admin` or **Email:** `admin@company.com`
* **Password:** `admin123`

---

## 3. Creating a New Customer Manager (Primary Method: Console UI)

No external tools or API commands are necessary. You can manage users directly in your browser:

### Step 1: Log in as the Administrator
1. Open the application in your browser (e.g., **http://localhost:3000**).
2. Enter the administrator credentials:
   * **Username/Email:** `admin` (or `admin@company.com`)
   * **Password:** `admin123`
3. Click **Sign In**.

### Step 2: Open the User Management Tab
Once logged in as `admin`, a **"Manage Users"** button will appear in the top navigation bar. Click on it to open the creation panel.

### Step 3: Fill Out the Creation Form
Complete the form with the new manager's profile:
1. **Username:** Must be alphanumeric only, with a minimum length of 3 characters (e.g., `manager2026`).
2. **Email Address:** The corporate email address of the manager.
3. **Full Name:** The display name of the manager.
4. **Password:** Must meet our strict TDD password security constraints:
   * Minimum of **8 characters** long.
   * At least **1 uppercase letter** (`A-Z`).
   * At least **1 lowercase letter** (`a-z`).
   * At least **1 digit** (`0-9`).
   * At least **1 special character** (e.g., `!@#$%^&*()`).

### Step 4: Submit
Click **Create Account**. On success, the inputs will be cleared, and a green success alert will confirm the account is active. The new manager can log in immediately.

---

## 4. Alternate Methods (Developers / APIs)

### Method A: Interactive Swagger UI
1. Navigate to **http://localhost:8000/api/docs**.
2. Click **Authorize** on the top right.
3. Enter `admin` as the username and `admin123` as the password, then authorize.
4. Open **POST `/api/v1/auth/signup`**, click **Try it out**, paste the JSON payload, and click **Execute**.

### Method B: Bash / Curl Terminal Command
1. **Obtain Access Token:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}'
   ```
2. **Register Account using token:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/signup" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer <TOKEN_RETURNED_ABOVE>" \
        -d '{"username": "johnsmith", "email": "john@company.com", "password": "StrongPassword123!"}'
   ```
