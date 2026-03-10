# Project: SauceDemo Test Execution Simulator

This project simulates a complete SauceDemo checkout flow test execution including:

1. **web-app** - SauceDemo application backend
2. **cart-service** - Cart data retrieval
3. **feature-flag-service** - Feature flag evaluation (with timeout failure)
4. **template-engine** - Cart and checkout page rendering
5. **test-runner** - Test automation execution logs
6. **page-objects** - Locator repository (with corrupted checkout button locator)
7. **locator-analyzer** - Root cause analysis of locator corruption

## Root Cause Simulation

The app simulates the exact TestScript failure where:

**Primary Issue: Corrupted Locator in Page Object Repository**
- Page object repository contains WRONG locator for checkout button
- Correct locator: `id='checkout'`
- Corrupted locator in repo: `id='checking out'` (invalid - contains space)
- Checkout button IS rendered in DOM with correct `id='checkout'`
- Test framework searches for corrupted locator and cannot find element

**Execution Flow:**
- Steps 1-13 pass successfully (login, add items, open cart)
- Feature flag service times out after 2000ms
- Checkout button is NOT rendered due to feature flag failure
- Step 14 fails: "Click on checkout" - element not found (button exists but locator is wrong)
- Steps 15-16 fail: Cannot find "First Name" field (cascading failure - still on cart page)
- Steps 17-23 skipped: Error threshold reached

**Key Evidence in Code:**
- `saucedemo_page_objects.py` - Contains corrupted locator repository
- `locator_corruption_analyzer.py` - Analyzes and logs the locator mismatch
- `template_engine.py` - Shows actual DOM structure with correct attributes

## API Endpoints

### `GET /cart.html`
Simulates the SauceDemo cart page request with feature flag timeout.

**Response:**
```json
{
  "cart": {"items": 1, "total": 29.99},
  "checkout_visible": false
}
```

### `GET /simulate-test`
Simulates complete test execution with all logs matching the RCA execution context.

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
  "cart": {...}
}
```

## Log Output

The simulator generates logs from multiple services:

- `test-runner` - Test execution steps and failures
- `web-app` - Application request handling
- `cart-service` - Cart data operations
- `feature-flag-service` - Feature flag evaluation
- `template-engine` - Template rendering

## Structure

```
sauce_demo_demo_app/
│
├── app/
│   ├── main.py
│   ├── logging_config.py
│   └── services/
│       ├── cart_service.py
│       ├── feature_flag_service.py
│       ├── template_engine.py
│       └── test_runner_simulator.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload

# Trigger test simulation
curl http://localhost:8000/simulate-test
```

## Expected Log Flow

1. Locator-analyzer logs corruption analysis (identifies wrong locators in repo)
2. Page-objects logs repository initialization with corrupted checkout locator
3. Test-runner logs steps 1-13 (PASSED)
4. Web-app receives GET /cart.html
5. Cart-service fetches cart for user U10293
6. Feature-flag-service evaluates ENABLE_CHECKOUT_BUTTON
7. Feature-flag-service times out after 2000ms
8. Web-app defaults checkout to false
9. Web-app logs checkout button will not be rendered
10. Template-engine renders cart template v1.13.0
11. Template-engine logs CRITICAL: checkout button NOT rendered in DOM
12. Test-runner attempts to locate checkout using corrupted locator from repo
13. Test-runner logs step 14 failure with 12 attempted corrupted locators
14. Test-runner logs navigation did not occur (still on cart page)
15. Test-runner logs steps 15-16 failures (cascading - wrong page)
16. Test-runner logs steps 17-23 skipped
17. Web-app completes response (~2300ms duration)