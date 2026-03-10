# SauceDemo Test Execution Simulator - Implementation Summary

## Overview

This FastAPI application now simulates a complete SauceDemo test execution flow, including both application logs and test-runner logs that match the RCA execution context.

## What Was Implemented

### 1. Enhanced Logging System (`app/logging_config.py`)
- Added support for metadata in log records
- Logs now include `attempted_locators` metadata for failed element searches
- JSON formatter outputs structured logs with service, level, message, time, and metadata

### 2. Test Runner Simulator (`app/services/test_runner_simulator.py`)
**New service that simulates complete test execution:**

- **Steps 1-13**: Successful test steps (browser open, login, add items, open cart)
- **Step 14**: Failed checkout button click with 12 attempted locators
- **Step 15**: Failed "First Name" field click with 6 attempted locators
- **Step 16**: Failed "First Name" field clear with 3 attempted locators
- **Steps 17-23**: Skipped steps due to error threshold

**Integrated Services:**
- Calls `cart_service.get_cart()` to fetch cart data
- Calls `feature_flag_service.is_checkout_enabled()` which times out
- Calls `template_engine.render_cart()` with checkout disabled
- Generates logs from multiple services: `test-runner`, `web-app`, `cart-service`, `feature-flag-service`, `template-engine`

### 3. Updated Main Application (`app/main.py`)
- Added new endpoint: `GET /simulate-test`
- Imports and exposes the test runner simulator
- Maintains existing `GET /cart.html` endpoint

### 4. Existing Services (Unchanged Core Logic)

**cart_service.py:**
- Fetches cart for user U10293
- 50ms async delay
- Returns cart with 1 item, total $29.99

**feature_flag_service.py:**
- Evaluates ENABLE_CHECKOUT_BUTTON flag
- 2000ms timeout simulation
- Raises TimeoutError with error log

**template_engine.py:**
- Renders cart template v1.12.4
- Logs warning when checkout button is skipped
- Returns cart data with checkout_visible flag

## Log Flow Simulation

When calling `GET /simulate-test`, the following log sequence is generated:

```
1. test-runner → "Starting test execution: sauce demo checkout flow"
2. test-runner → "Browser: chrome"
3. test-runner → "Test ID: 2544"
4. test-runner → Steps 1-13 PASSED logs
5. web-app → "Incoming request GET /cart.html"
6. cart-service → "Fetching cart for user_id=U10293"
7. cart-service → "Cart response items=1 total=29.99"
8. feature-flag-service → "Evaluating feature flag ENABLE_CHECKOUT_BUTTON for user_id=U10293"
9. [2 second delay]
10. feature-flag-service → "Feature flag service timeout after 2000ms"
11. web-app → "Feature flag ENABLE_CHECKOUT_BUTTON defaulted to false due to service failure"
12. web-app → "Checkout button will not be rendered for this session"
13. template-engine → "Rendering cart template version=v1.12.4"
14. template-engine → "Skipping component <CheckoutButton /> due to feature flag false"
15. test-runner → "Step 14: Click on 'checkout' - FAILED"
16. test-runner → "Element not found for locator checkout" (with metadata)
17. test-runner → 12 individual locator failure logs
18. test-runner → "Step 15: Click on 'First Name' - FAILED"
19. test-runner → "Element not found for locator First Name" (with metadata)
20. test-runner → 6 individual locator failure logs
21. test-runner → "Step 16: Clear text from input field 'First Name' - FAILED"
22. test-runner → 3 individual locator failure logs
23. test-runner → Steps 17-23 SKIPPED logs
24. web-app → "Response completed GET /cart.html status=200 duration_ms=2347"
25. test-runner → "Test execution completed with FAILURES"
26. test-runner → "Total steps: 23 | Passed: 13 | Failed: 3 | Skipped: 7"
```

## API Endpoints

### `GET /cart.html`
Simulates just the cart page request (backend only).

**Response:**
```json
{
  "cart": {"items": 1, "total": 29.99},
  "checkout_visible": false
}
```

### `GET /simulate-test` (NEW)
Simulates complete test execution with all logs.

**Response:**
```json
{
  "test_name": "sauce demo checkout flow",
  "status": "failed",
  "total_steps": 23,
  "passed": 13,
  "failed": 3,
  "skipped": 7,
  "checkout_button_rendered": false,
  "cart": {
    "cart": {"items": 1, "total": 29.99},
    "checkout_visible": false
  }
}
```

## Testing the Simulation

### Option 1: Run the FastAPI Server
```bash
uvicorn app.main:app --reload
```

Then call:
```bash
curl http://localhost:8000/simulate-test
```

### Option 2: Run the Test Script Directly
```bash
python test_simulation.py
```

## Key Features

✅ **Complete Test Flow**: Simulates all 23 test steps
✅ **Multi-Service Logs**: Generates logs from 5 different services
✅ **Realistic Timing**: 2-second feature flag timeout, ~2.3s total duration
✅ **Metadata Support**: Includes attempted_locators in error logs
✅ **Cascading Failures**: Steps 15-16 fail due to step 14, steps 17-23 skipped
✅ **JSON Structured Logs**: All logs in JSON format with timestamp, level, service, message
✅ **SauceDemo Context**: All logs reference SauceDemo-specific elements and flow

## RCA Relevance

This simulation now provides:

1. **Test Execution Context**: Complete test flow with step IDs, actions, and statuses
2. **Application Logs**: Backend service logs showing feature flag timeout
3. **Test Runner Logs**: Element locator attempts and failures
4. **Cascading Failure Chain**: Clear cause-and-effect relationship between failures
5. **Metadata**: Structured attempted_locators data for RCA analysis

The code knowledge base now contains relevant code that explains:
- Why the checkout button wasn't rendered (feature flag timeout)
- What locators were attempted (in test_runner_simulator.py)
- The complete execution flow (test steps → backend services → failures)

## Files Modified/Created

**Modified:**
- `app/main.py` - Added simulate-test endpoint
- `app/logging_config.py` - Added metadata support
- `README.md` - Updated documentation

**Created:**
- `app/services/test_runner_simulator.py` - Complete test execution simulator
- `test_simulation.py` - Standalone test script
- `IMPLEMENTATION_SUMMARY.md` - This file
