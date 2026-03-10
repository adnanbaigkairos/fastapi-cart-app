# Project: SauceDemo Test Execution Simulator

This project simulates a complete SauceDemo checkout flow test execution including:

1. **web-app** - SauceDemo application backend
2. **cart-service** - Cart data retrieval
3. **feature-flag-service** - Feature flag evaluation (with timeout failure)
4. **template-engine** - Cart page rendering
5. **test-runner** - Test automation execution logs

## Simulation Scenario

The app simulates the exact failure scenario where:
- Test executes SauceDemo checkout flow (steps 1-23)
- Steps 1-13 pass successfully (login, add items, open cart)
- Feature flag service times out after 2000ms
- Checkout button is NOT rendered due to feature flag failure
- Step 14 fails: "Click on checkout" - element not found
- Steps 15-16 fail: Cannot find "First Name" field (wrong page)
- Steps 17-23 skipped: Error threshold reached

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

1. Test-runner logs steps 1-13 (PASSED)
2. Web-app receives GET /cart.html
3. Cart-service fetches cart for user U10293
4. Feature-flag-service evaluates ENABLE_CHECKOUT_BUTTON
5. Feature-flag-service times out after 2000ms
6. Web-app defaults checkout to false
7. Web-app logs checkout button will not be rendered
8. Template-engine renders cart template v1.12.4
9. Template-engine skips CheckoutButton component
10. Test-runner logs step 14 failure with attempted locators
11. Test-runner logs steps 15-16 failures (cascading)
12. Test-runner logs steps 17-23 skipped
13. Web-app completes response (~2300ms duration)