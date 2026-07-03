# Customer UI Wireframes

This document details the interface layouts for the customer management and prediction screens.

---

## 1. Customer Search & List View
This page allows administrators to search and filter through the customer database.

```text
+--------------------------------------------------------------------------------------------------+
|  [Logo] Churn Analytics System                   Dashboard | Customers | Reports | Model Performance |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|  CUSTOMER REPOSITORY (Total: 15,946)                                                             |
|                                                                                                  |
|  +--------------------------------------------------------------------------------------------+  |
|  | Search by ID: [ C10239            ]                                                        |  |
|  |                                                                                            |  |
|  | Filters:                                                                                   |  |
|  | Risk Category: [ All v ]  Income Level: [ Medium v ]  Payment Mode: [ UPI v ]             |  |
|  |                                                                         [ Reset ] [ Apply ]|  |
|  +--------------------------------------------------------------------------------------------+  |
|                                                                                                  |
|  +--------------------------------------------------------------------------------------------+  |
|  | Customer ID | Age | Income | Monthly Spend | Tenure  | Risk Score | Status     | Actions    |  |
|  +-------------+-----+--------+---------------+---------+------------+------------+------------+  |
|  | C10239      | 34  | Medium | $79.99        | 12 mos  | 84.50%     | HIGH RISK  | [ View ]   |  |
|  | C10452      | 45  | High   | $120.00       | 24 mos  | 12.10%     | LOW RISK   | [ View ]   |  |
|  +--------------------------------------------------------------------------------------------+  |
|  |  << First  < Prev   Page 1 of 1595   Next >  Last >>                       Show [ 10 v ]/page |  |
|  +--------------------------------------------------------------------------------------------+  |
|                                                                                                  |
+--------------------------------------------------------------------------------------------------+