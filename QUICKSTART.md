# Quick Start Guide

## Installation

```bash
# Navigate to project directory
cd sauce_demo_demo_app

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

### Method 1: FastAPI Server (Recommended)

```bash
# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

### Method 2: Direct Python Script

```bash
# Run the simulation directly
python test_simulation.py
```

## Testing the Endpoints

### Simulate Complete Test Execution

```bash
# Using curl
curl http://localhost:8000/simulate-test

# Using browser
# Navigate to: http://localhost:8000/simulate-test
```

**Expected Output:**
- Console logs showing complete test execution flow
- JSON response with test results

### Cart Page Only (Backend Simulation)

```bash
# Using curl
curl http://localhost:8000/cart.html

# Using browser
# Navigate to: http://localhost:8000/cart.html
```

**Expected Output:**
- Backend service logs (cart, feature flag, template)
- JSON response with cart data and checkout visibility

## Viewing Logs

All logs are output to the console in JSON format. Each log includes:
- `level`: info, warning, error
- `service`: test-runner, web-app, cart-service, feature-flag-service, template-engine
- `message`: Log message
- `time`: ISO timestamp
- `metadata`: Additional data (for error logs with attempted locators)

### Example Log Output

```json
{"level": "info", "service": "test-runner", "message": "Starting test execution: sauce demo checkout flow", "time": "2026-03-10T12:00:00.000000"}
{"level": "info", "service": "web-app", "message": "Incoming request GET /cart.html", "time": "2026-03-10T12:00:01.500000"}
{"level": "info", "service": "cart-service", "message": "Fetching cart for user_id=U10293", "time": "2026-03-10T12:00:01.510000"}
{"level": "error", "service": "feature-flag-service", "message": "Feature flag service timeout after 2000ms", "time": "2026-03-10T12:00:03.510000"}
{"level": "error", "service": "test-runner", "message": "Element not found for locator checkout", "time": "2026-03-10T12:00:03.620000", "metadata": {"attempted_locators": ["By.xpath: //button[@idqksm='checksalxmout']", "..."]}}
```

## Understanding the Simulation

### The Scenario

This simulation recreates a real-world test failure scenario:

1. **Test starts**: Automated test begins executing SauceDemo checkout flow
2. **Steps 1-13 pass**: Login, add items to cart, open cart page
3. **Backend timeout**: Feature flag service times out (2000ms)
4. **UI impact**: Checkout button is NOT rendered
5. **Test fails**: Step 14 cannot find checkout button
6. **Cascading failures**: Steps 15-16 fail (wrong page), steps 17-23 skipped

### Why This Matters for RCA

This simulation demonstrates:
- **Root Cause**: Backend feature flag timeout
- **UI Impact**: Missing checkout button
- **Test Impact**: Element not found errors
- **Cascading Effect**: Multiple downstream failures

The RCA system can now analyze:
- Backend logs showing the timeout
- Test logs showing locator attempts
- The causal chain from backend → UI → test failure

## API Documentation

### `GET /simulate-test`

**Description**: Simulates complete SauceDemo test execution with all 23 steps

**Response**: 
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

**Duration**: ~2.5 seconds (includes 2s feature flag timeout)

### `GET /cart.html`

**Description**: Simulates SauceDemo cart page request (backend only)

**Query Parameters**:
- `user_id` (optional): User ID, defaults to "U10293"

**Response**:
```json
{
  "cart": {
    "items": 1,
    "total": 29.99
  },
  "checkout_visible": false
}
```

**Duration**: ~2.1 seconds (includes 2s feature flag timeout)

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

## Next Steps

1. **Integrate with RCA System**: Point your RCA system to this endpoint
2. **Customize Scenarios**: Modify `test_runner_simulator.py` to create different failure scenarios
3. **Add More Services**: Extend with additional backend services as needed
4. **Export Logs**: Pipe logs to a file or logging service for analysis

## Support

For issues or questions, refer to:
- `README.md` - Project overview
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- Code comments in `app/services/test_runner_simulator.py`
