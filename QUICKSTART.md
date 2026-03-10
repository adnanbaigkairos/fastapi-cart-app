# Quick Start Guide

## Installation

```bash
# Navigate to project directory
cd sauce_demo_demo_app

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

```bash
# Start the SauceDemo backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will start at `http://localhost:8000`

## Testing the Application

### Access Cart Page

```bash
# Using curl
curl http://localhost:8000/cart.html

# Using browser
# Navigate to: http://localhost:8000/cart.html
```

**Expected Behavior:**
- Feature flag service will timeout after 2000ms
- Checkout button will NOT be rendered in the response
- Console logs will show the complete backend flow
- Response time: ~2100ms

### Access Checkout Page

```bash
# Using curl
curl http://localhost:8000/checkout-step-one.html

# Using browser
# Navigate to: http://localhost:8000/checkout-step-one.html
```

**Expected Behavior:**
- Returns checkout information form
- Contains first-name, last-name, postal-code input fields

## Viewing Application Logs

All logs are output to the console in JSON format. Each log includes:
- `level`: info, warning, error
- `message`: Log message
- `time`: ISO timestamp

### Example Log Output

```json
{"level": "info", "message": "Incoming request GET /cart.html", "time": "2026-03-10T12:00:00.000000"}
{"level": "info", "message": "Fetching SauceDemo cart for user_id=U10293", "time": "2026-03-10T12:00:00.010000"}
{"level": "info", "message": "Cart retrieved successfully: items=1 total=$29.99", "time": "2026-03-10T12:00:00.060000"}
{"level": "info", "message": "Evaluating feature flag ENABLE_CHECKOUT_BUTTON for user_id=U10293", "time": "2026-03-10T12:00:00.070000"}
{"level": "error", "message": "Feature flag service timeout after 2000ms", "time": "2026-03-10T12:00:02.070000"}
{"level": "warning", "message": "Feature flag ENABLE_CHECKOUT_BUTTON defaulted to false due to service failure", "time": "2026-03-10T12:00:02.071000"}
{"level": "error", "message": "CRITICAL: Checkout button NOT rendered in DOM - element with id='checkout' will not exist", "time": "2026-03-10T12:00:02.080000"}
{"level": "info", "message": "Response completed GET /cart.html status=200 duration_ms=2100", "time": "2026-03-10T12:00:02.100000"}
```

## Understanding the Application Behavior

### The Backend Issue

This application demonstrates a real backend failure:

1. **Request arrives**: User/test navigates to cart page
2. **Cart loads**: Cart service successfully retrieves cart data
3. **Feature flag check**: Application calls feature flag service
4. **Timeout occurs**: Feature flag service times out after 2000ms
5. **Fallback behavior**: Application defaults to `checkout_enabled=false`
6. **UI impact**: Template engine does NOT render checkout button in HTML
7. **Result**: The HTML response lacks `<button id="checkout">` element

### Why This Causes Test Failures

When automated tests run against this application:
- Test expects to find checkout button with `id="checkout"`
- Button does NOT exist in the DOM (not rendered)
- Test fails with "Element not found" error
- Subsequent steps fail because navigation to checkout page never occurs

### Root Cause

**Backend Issue:** Feature flag service timeout (2000ms)
**Impact:** Checkout button not rendered in cart page HTML
**Evidence:** Application logs show timeout and explicit warning about button not being rendered

## API Documentation

### `GET /cart.html`

**Description**: Returns SauceDemo cart page with items

**Query Parameters**:
- `user_id` (optional): User ID, defaults to "U10293"

**Response**:
```json
{
  "cart": {
    "items": 1,
    "total": 29.99,
    "products": [
      {
        "id": 4,
        "name": "Sauce Labs Backpack",
        "price": 29.99,
        "quantity": 1
      }
    ]
  },
  "checkout_visible": false,
  "html_rendered": "<div id='cart_contents_container'>...</div>",
  "page": "cart",
  "url": "https://www.saucedemo.com/cart.html"
}
```

**Duration**: ~2100ms (includes 2000ms feature flag timeout)

**Note**: `checkout_visible: false` means the checkout button is NOT in the HTML

### `GET /checkout-step-one.html`

**Description**: Returns SauceDemo checkout information form page

**Response**:
```json
{
  "html_rendered": "<div id='checkout_info_container'>...</div>",
  "page": "checkout_step_one",
  "url": "https://www.saucedemo.com/checkout-step-one.html"
}
```

**Duration**: ~10ms

## Troubleshooting

### Port Already in Use

```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```

### Import Errors

```bash
# Ensure you're in the project root directory
cd sauce_demo_demo_app

# Reinstall dependencies
pip install -r requirements.txt
```

### No Logs Appearing

- Logs are written to stdout/console
- Check that logging level is INFO or lower
- Ensure the service loggers are properly initialized

## Code Structure for RCA Analysis

The codebase contains the actual application code that causes the test failure:

1. **`app/main.py`** - FastAPI endpoints for cart and checkout pages
2. **`app/services/cart_service.py`** - Cart data retrieval logic
3. **`app/services/feature_flag_service.py`** - Feature flag evaluation (TIMES OUT after 2000ms)
4. **`app/services/template_engine.py`** - HTML rendering logic that SKIPS checkout button when flag is false

### Key Code to Review

**Feature Flag Service** (`feature_flag_service.py`):
- Line 13: `await asyncio.sleep(2)` - Causes 2000ms timeout
- Line 15: Raises `TimeoutError`

**Template Engine** (`template_engine.py`):
- Line 19-24: Conditional rendering of checkout button
- When `show_checkout=False`, button is NOT added to HTML

**Main Application** (`main.py`):
- Line 23-30: Catches `TimeoutError` and defaults to `checkout_enabled=False`
- This causes template engine to skip rendering the button
