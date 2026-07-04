# Authentication UI Design

This document details the visual, interactive, and structural design for the Administrator login and sign-up interfaces.

## 1. Visual System Tokens

* **Primary Background**: Sleek deep gray/black `#0F0F11` (dark mode by default).
* **Accent Color**: Electric blue HSL gradient:
  * Primary: `hsl(217, 91%, 60%)` (#3B82F6)
  * Secondary: `hsl(263, 62%, 50%)` (#6366F1)
* **Card Element**: Glassmorphism effect:
  * Background: `rgba(25, 25, 29, 0.65)`
  * Border: `1px solid rgba(255, 255, 255, 0.08)`
  * Backdrop Blur: `20px`
* **Typography**: Google Fonts: **Inter** or **Outfit** for clean technical layout.

## 2. Page Wireframe & Layout

### Central Login Card Layout
```text
+------------------------------------------+
|                  (Logo)                  |
|        Subscription Churn Predictor      |
|                                          |
|  Email/Username                          |
|  [ admin@company.com                  ]  |
|                                          |
|  Password                                |
|  [ ************                    (o) ]  |
|                                          |
|  [x] Remember me                         |
|                                          |
|  +------------------------------------+  |
|  |             Sign In                |  |
|  +------------------------------------+  |
|                                          |
|  Credentials issue? Contact Tech Lead    |
+------------------------------------------+
```

## 3. UI Interaction States

### Under Focus / Active inputs
* Focus Outline: `2px solid hsl(217, 91%, 60%)`
* Smooth transition speed: `cubic-bezier(0.4, 0, 0.2, 1)` with `0.2s` duration.
* Background shade darkens slightly.

### Button Hover State
* Slight scale: `scale(1.02)`
* Backlight glow: `box-shadow: 0 0 20px rgba(59, 130, 246, 0.4)`

### Error Feedback Flow
* Input border turns red: `1px solid #EF4444`.
* Translucent red warning alert container slides down from the top of the card using a smooth slide/fade animation.
