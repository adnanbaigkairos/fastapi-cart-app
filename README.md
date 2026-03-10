# SauceDemo Application - Cart & Checkout Backend

This is the **SauceDemo web application backend** that serves the cart and checkout pages.

## Application Architecture

1. **saucedemo-web-app** - Main FastAPI application serving cart and checkout pages
2. **cart-service** - Retrieves cart data from database
3. **feature-flag-service** - Evaluates feature flags for UI rendering decisions
4. **template-engine** - Renders HTML for cart and checkout pages

## The Issue

When the feature flag service times out (2000ms), the checkout button is NOT rendered in the cart page DOM.

**What happens:**
1. User adds items to cart and navigates to `/cart.html`
2. Application fetches cart data successfully
3. Application calls feature flag service to check `ENABLE_CHECKOUT_BUTTON`
4. Feature flag service times out after 2000ms
5. Application defaults to `checkout_enabled=false`
6. Template engine renders cart page WITHOUT the checkout button
7. The checkout button element (`id="checkout"`) does NOT exist in the DOM

**Impact:**
- Any test automation looking for the checkout button will fail
- Users cannot proceed to checkout
- The button is simply not present in the HTML response

## API Endpoints

### `GET /cart.html`
Returns the cart page with items. Checkout button visibility depends on feature flag service.

**Response:**
```json
{
  "cart": {
    "items": 1,
    "total": 29.99,
    "products": [...]
  },
  "checkout_visible": false,
  "html_rendered": "<div id='cart_contents_container'>...</div>",
  "page": "cart",
  "url": "https://www.saucedemo.com/cart.html"
}
```

### `GET /checkout-step-one.html`
Returns the checkout information form page.

**Response:**
```json
{
  "html_rendered": "<div id='checkout_info_container'>...</div>",
  "page": "checkout_step_one",
  "url": "https://www.saucedemo.com/checkout-step-one.html"
}
```

## Application Logs

The application generates logs from multiple backend services:

- `saucedemo-web-app` - Main application request handling
- `cart-service` - Cart data retrieval from database
- `feature-flag-service` - Feature flag evaluation (times out after 2000ms)
- `template-engine` - HTML template rendering for cart and checkout pages

## Project Structure

```
sauce_demo_demo_app/
│
├── app/
│   ├── main.py                    # FastAPI application (cart & checkout endpoints)
│   ├── logging_config.py          # Logging configuration
│   └── services/
│       ├── cart_service.py        # Cart data retrieval
│       ├── feature_flag_service.py # Feature flag evaluation (times out)
│       └── template_engine.py     # HTML rendering for pages
│
├── requirements.txt
└── README.md
```

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000

# Access cart page
curl http://localhost:8000/cart.html
```

## Expected Application Log Flow

When a request is made to `/cart.html`:

1. `saucedemo-web-app` → "Incoming request GET /cart.html"
2. `cart-service` → "Fetching SauceDemo cart for user_id=U10293"
3. `cart-service` → "Cart retrieved successfully: items=1 total=$29.99"
4. `feature-flag-service` → "Evaluating feature flag ENABLE_CHECKOUT_BUTTON for user_id=U10293"
5. `feature-flag-service` → "Connecting to feature flag service at https://flags.saucedemo.internal/api/v1/evaluate"
6. [2000ms delay]
7. `feature-flag-service` → "Feature flag service timeout after 2000ms"
8. `feature-flag-service` → "Failed to retrieve feature flag value from remote service"
9. `feature-flag-service` → "This timeout will cause checkout button to NOT be rendered in cart page DOM"
10. `saucedemo-web-app` → "Feature flag ENABLE_CHECKOUT_BUTTON defaulted to false due to service failure"
11. `saucedemo-web-app` → "Checkout button will not be rendered for this session"
12. `template-engine` → "Rendering SauceDemo cart page template version=v1.13.0"
13. `template-engine` → "Skipping component <CheckoutButton id='checkout' /> due to feature flag ENABLE_CHECKOUT_BUTTON=false"
14. `template-engine` → "CRITICAL: Checkout button NOT rendered in DOM - element with id='checkout' will not exist"
15. `template-engine` → "Cart page rendered successfully. Checkout button present in DOM: false"
16. `saucedemo-web-app` → "Response completed GET /cart.html status=200 duration_ms=2100"

**Result:** The HTML response does NOT contain `<button id="checkout">` element