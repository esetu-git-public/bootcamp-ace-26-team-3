# React & Material-UI Analytics UI Design Plan

This document establishes the UI/UX architecture, page layouts, component hierarchies, and interactive charting specifications for the **Subscription Cancellation Prediction System** frontend application.

The frontend is built using **React.js**, **Material UI (MUI v5)** for components, and **Recharts** for premium, lightweight, responsive data visualizations.

---

## 1. Visual Identity & Theme Definition

To deliver a premium, high-impact user experience, the system utilizes a **dark-mode glassmorphism** theme with high-contrast glowing accents.

### Color Palette (MUI Theme Configuration)
```javascript
const themeOptions = {
  palette: {
    mode: 'dark',
    primary: {
      main: '#6366f1', // Indigo / Purple glow
      light: '#818cf8',
    },
    secondary: {
      main: '#06b6d4', // Vibrant Teal
      light: '#22d3ee',
    },
    background: {
      default: '#0b0f19', // Deep charcoal-blue canvas
      paper: 'rgba(17, 24, 39, 0.7)', // Semi-transparent card body
    },
    success: {
      main: '#10b981', // Emerald Green (Low Risk)
    },
    warning: {
      main: '#f59e0b', // Amber Yellow (Medium Risk)
    },
    error: {
      main: '#ef4444', // Crimson Red (High Risk / Churn)
    },
    text: {
      primary: '#f3f4f6',
      secondary: '#9ca3af',
    },
  },
  typography: {
    fontFamily: "'Outfit', 'Inter', sans-serif",
    h1: { fontWeight: 700 },
    h5: { fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 500 },
  },
};
```

### Key Design Elements
* **Glassmorphism Backdrop Filter**: All dashboard cards use semi-transparent background colors combined with CSS properties:
  ```css
  background: rgba(17, 24, 39, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
  border-radius: 12px;
  ```
* **Micro-Animations**: CSS transitions (`all 0.3s ease-in-out`) are added to all buttons, navigation items, and datagrid rows to trigger subtle hover-glows and scaling factors.
* **Interactive Tooltips**: Recharts tooltips are custom-rendered using styled HTML/CSS nodes matching the glassmorphism card styles.

---

## 2. Page Layours & Component Outlines

### Screen 1: Executive Dashboard (Landing Page)
An overall business perspective on subscription health.

#### High-Fidelity Design Mockup
![Executive Dashboard Mockup](/C:/Users/goske/.gemini/antigravity-ide/brain/2de4e94f-c639-404d-9359-4ebe0f338cbe/executive_dashboard_mockup_1783075214135.png)

#### Component Structure:
1. **Metric Grid (MUI `Grid` Container)**:
   * Four KPI cards displaying:
     * **Total Customers**: Count (e.g. `15,946`) with active sparkline.
     * **Predicted Churn**: Count (e.g. `1,977`) and percentage of database.
     * **Avg Churn Risk**: Percentage gauge value (e.g. `12.4%`).
     * **Monthly Revenue at Risk**: Absolute value in USD (e.g. `$45,210`).
   * *Sparkline Specification*: Light-weight `AreaChart` with no grid lines, axes, or tooltips. Glowing colored stroke matching the KPI context (e.g., indigo for Total, crimson red for Churn).
2. **Main Layout Widgets**:
   * **Left Card (Churn Risk Breakdown)**: An interactive `PieChart` or `RadialBarChart` demonstrating Low, Medium, and High risk segments. Clicking a slice updates the table below to show that specific segment's customers.
   * **Right Card (Revenue Loss Projection)**: A linear gauge displaying projected revenue losses over the next 30, 60, and 90 days.
3. **Escalation Table (High-Risk Customer List)**:
   * Data table displaying the Top 5 customers ordered by Churn Probability DESC.
   * Row details: Customer ID, Tenure, Risk Probability (visual progress bar indicator), and an action button to open their details page.

---

### Screen 2: Interactive Analytics View
Deep-dive charts demonstrating correlations, behavior, and demographics.

#### Component Structure:
1. **Demographic Segment Grid**:
   * **Income vs Churn Rate**: Stacked `BarChart` comparing Churn/No Churn distributions inside Low, Medium, and High income groups.
   * **Customer Distribution by Device**: `RadarChart` indicating active device preferences.
2. **Behavior & Spend Correlation (Recharts `ScatterChart`)**:
   * **High-Impact Chart**: X-axis: `avg_usage_hours_per_week`, Y-axis: `monthly_total_spend`.
   * Individual dots represent customer records.
   * Dot colors correspond to risk levels: Low (Green), Medium (Amber), High (Crimson).
   * Visualizes high-spending, low-engagement customers (who form the core cohort of high churn risk).
3. **Satisfaction Correlation (Clustered `BarChart`)**:
   * Compares satisfaction scores (1 to 5) with churn rate and average support interactions to highlight friction points.

---

### Screen 3: Customer Search & Filter (Directory)
Search interface for customer lists.

#### Component Structure:
1. **Sidebar Filter Panel (Collapsible MUI `Drawer`)**:
   * Checkbox/Dropdown groups: Income Levels, Device Types, Payment Modes, and Risk Category.
   * Clear Filters button, Active Filter Chips count indicator.
2. **Datagrid Area (MUI `DataGrid` or custom table)**:
   * Displays rows returned by `GET /api/v1/customers`.
   * Columns: Customer ID, Age, Monthly Spend ($), Satisfaction, Churn Risk (color-coded badge), Action link.
   * Features interactive sorting on Churn Probability and Tenure fields.
   * Pagination toolbar at bottom matching limits/offsets.

---

### Screen 4: Customer Profile & Churn Insights
Actionable intelligence for a single customer.

#### High-Fidelity Design Mockup
![Customer Profile Mockup](/C:/Users/goske/.gemini/antigravity-ide/brain/2de4e94f-c639-404d-9359-4ebe0f338cbe/customer_profile_mockup_1783075268003.png)

#### Component Structure:
1. **Left Card: Customer Demographics & Behavioral Summary**:
   * Grid display showing key metrics (Age, Tenure, Spend, Device Type, Support Tickets, Satisfaction).
   * Quick status chips indicating active status and discount history.
2. **Center Card: Explainable AI & Risk Score Gauge**:
   * **Circular Progress Gauge**: Large center dial indicating the customer's churn risk score (e.g. `89.0%`). Color shifts dynamically: Green (<30%), Orange (30%-69%), Red (>=70%).
   * **SHAP Explainability Insights (Horizontal `BarChart`)**: Displays factors pushing the prediction high or low. Pushes (e.g. +3 Support interactions) are colored red; pulls (e.g. +14 usage hours) are colored green.
3. **Right Card: Retention Recommendation Engine**:
   * Recommends personalized offers generated by database rules.
   * Includes descriptive cards explaining why the action was selected (e.g., "Customer has high monthly spend and low usage. Recommend a 20% discount offer to incentivize renewal").
   * **Action Button**: Trigger button to "Apply Offer" or "Log Retention Action", which updates the database in a single click.

---

### Screen 5: Model Performance Dashboard
Technical view of model evaluation and features.

#### Component Structure:
1. **ML Metric Card Row**:
   * 5 cards with performance scores: Accuracy (e.g., `85.4%`), Precision, Recall, F1, and ROC-AUC.
2. **Confusion Matrix Grid**:
   * A 2x2 colored grid visualizing True Positives, False Positives, True Negatives, and False Negatives, complete with percentages.
3. **Feature Importance Ranking**:
   * Horizontal `BarChart` displaying weight parameters returned from the FastAPI endpoint (e.g. `Tenure_Months` and `Customer_Support_Interactions` as top factors).

---

## 3. Frontend Routing Plan (React Router)

All dashboard pages are contained inside an authenticated main layout:

* `/` or `/dashboard` -> `DashboardLayout` wrapping:
  * `/dashboard` -> `ExecutiveDashboard`
  * `/dashboard/analytics` -> `AnalyticsView`
  * `/dashboard/customers` -> `CustomerDirectory`
  * `/dashboard/customers/:id` -> `CustomerProfile`
  * `/dashboard/model` -> `ModelPerformance`
* `/login` -> Public `Login` page
