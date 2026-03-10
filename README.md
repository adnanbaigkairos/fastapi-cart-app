# SauceDemo Checkout Backend

FastAPI backend for the SauceDemo e-commerce checkout flow. All services, DB access, and routing live in a single file (`src/main.py`) for simplicity.

---

## Project Structure

```
src/
└── main.py          # All services, DB layer, and routes in one file
logs/
└── app.log          # Structured JSON logs (used by RCA agent)
README.md
requirements.txt
```

---

## Architecture Overview

All logic is colocated in `src/main.py` in the following layers:

```
POST /api/v1/checkout/init
        │
        ▼
[Route: init_checkout]          line 187
        │
        ├── get_cart()           line 125  →  find_cart_by_id()      line 38   →  cart_db (asyncpg)
        ├── lock_cart()          line 131  →  acquire_cart_lock()    line 64   →  pg_advisory_xact_lock
        ├── validate_stock()     line 143  →  get_product_stock()    line 87   →  inventory table
        ├── calculate_total()    line 161  →  TAX_RATE + SHIPPING    line 158
        ├── create_session()     line 171  →  generates CHK_xxxxx UUID
        └── persist_checkout_session()     line 104  →  checkout_sessions table
```

---

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (RDS `db.t3.medium` or higher — see [Known Issues](#known-issues))
- pip

### Install

```bash
pip install fastapi uvicorn asyncpg python-dotenv
```

### Environment Variables

```env
DATABASE_URL=postgresql://user:password@localhost:5432/saucedemo
```

### Run

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## API Reference

### `POST /api/v1/checkout/init`

Initiates a checkout session for an authenticated user's cart.

**Request**
```json
{
  "cart_id": "CRT_88821"
}
```

**Headers**
```
Authorization: Bearer <session_token>
```

**Success Response — `200 OK`**
```json
{
  "checkout_id": "CHK_44521",
  "status": "initiated"
}
```

**Error Responses**

| Status | Error Code | Cause |
|--------|------------|-------|
| `500` | `CART_LOCK_TIMEOUT` | Cart row lock held by concurrent session (see line 74) |
| `500` | `DB_POOL_EXHAUSTED` | asyncpg connection pool exhausted (see line 119) |
| `500` | `DB_WRITE_FAILED` | Postgres error during INSERT (see line 122) |
| `500` | `Insufficient stock for product_id=X` | Stock validation failed (see line 152) |

> ⚠️ All errors currently return `status=500`. See [Known Issues](#known-issues) for the planned fix to distinguish retryable vs non-retryable errors.

---

## DB Pool Configuration

Configured at `src/main.py:24`:

```python
POOL_MIN_SIZE = 5
POOL_MAX_SIZE = 50        # ← See Known Issues: PLAT-4421
POOL_COMMAND_TIMEOUT = 30
```

**Connection consumption per checkout request:**

| Step | Function | Pool Connections Opened |
|------|----------|------------------------|
| Fetch cart | `find_cart_by_id()` line 38 | 1 |
| Lock cart | `acquire_cart_lock()` line 64 | 1 |
| Validate stock | `get_product_stock()` line 87 | 1 per cart item |
| Persist session | `persist_checkout_session()` line 104 | 1 |
| Release lock (on failure) | `release_cart_lock()` line 76 | 1 |
| **Total (2-item cart)** | | **5 connections** |

> A 2-item cart checkout consumes 5 pool connections sequentially. A 10-item cart consumes 13.

---

## Cart Locking

Cart locking uses PostgreSQL advisory locks (`pg_advisory_xact_lock`) at `src/main.py:70`.

**Lock acquire:**
```python
await conn.execute("SELECT pg_advisory_xact_lock($1)", hash(cart_id))   # line 70
```

**Lock release:**
```python
await conn.execute("SELECT pg_advisory_unlock($1)", hash(cart_id))      # line 80
```

> ⚠️ `pg_advisory_xact_lock` is **session-scoped**, not transaction-scoped. If a checkout crashes before `release_cart_lock()` is called, the lock persists on that connection until the connection is closed by the pool. This is the root cause of `CART_LOCK_TIMEOUT` errors seen in prod. See ticket `CART-887`.

---

## Pricing Logic

Configured at `src/main.py:158`:

```python
TAX_RATE = 0.08           # Flat 8% — hardcoded, not region-aware (see PRICING-55)
SHIPPING_FLAT_RATE = 5.99 # Flat rate — no carrier API call
```

> ⚠️ Tax rate is not fetched from a tax service at runtime. If a user's region changes between cart load and checkout submission, the tax amount will be stale. Multi-region tax logic is tracked in `PRICING-55`.

---

## Logging

All logs are emitted as structured JSON via Python's standard `logging` module:

```python
logger.info({"service": "cart-service", "message": f"Fetching cart cart_id={cart_id} user_id={user_id}"})
```

**Log services and their source locations:**

| Service Tag | Layer | Lines |
|-------------|-------|-------|
| `web-app` | Route entry/exit | 192, 211 |
| `cart-service` | Cart service functions | 126–140 |
| `cart-db` | Cart DB acquire lock | 72 |
| `inventory-service` | Stock validation | 115–152 |
| `pricing-service` | Total calculation | 127–133 |
| `checkout-service` | Session creation + error catch | 138, 169, 209 |
| `checkout-db` | DB persist + error | 105, 117, 121 |
| `alerting` | Pool exhaustion alert | — |

**Log levels used:**

| Level | Meaning |
|-------|---------|
| `info` | Normal flow — request received, step completed |
| `warn` | Degraded path — lock release on failure, retry attempt |
| `error` | Hard failure — lock timeout, pool exhausted, DB write failed |

---

## Known Issues

### PLAT-4421 — DB Connection Pool Exhaustion (P0)
- **Location:** `src/main.py:32` (`POOL_MAX_SIZE = 50`)
- **Problem:** 6 prod nodes × 50 connections = 300 potential connections. RDS `db.t3.medium` hard cap is **170**. Under checkout traffic spikes, pool slots fill instantly across nodes, starving each other.
- **Symptom in logs:** `error=POOL_EXHAUSTED active_connections=50 max_connections=50 wait_queue=12`
- **Fix:** Reduce `POOL_MAX_SIZE` to `15` per node (6×15=90 < 170), or deploy PgBouncer as a connection pooler in front of RDS.

### CART-887 — Ghost Lock from Crashed Sessions (P0)
- **Location:** `src/main.py:70` (`pg_advisory_xact_lock`)
- **Problem:** Advisory lock is session-scoped. If `release_cart_lock()` is skipped due to a crash or pool exhaustion in the except block itself (line 211), the lock remains held until the DB connection is recycled. Next checkout attempt on the same `cart_id` hits `CART_LOCK_TIMEOUT`.
- **Symptom in logs:** `lock held by concurrent session error=ER_LOCK_WAIT_TIMEOUT`
- **Fix:** Replace `pg_advisory_xact_lock` with `pg_try_advisory_lock` inside an explicit transaction, or use `SELECT ... FOR UPDATE SKIP LOCKED` on the carts table.

### INV-210 — Per-Item DB Connection in Stock Validation (P1)
- **Location:** `src/main.py:150` (`get_product_stock()` inside loop)
- **Problem:** Each item in the cart opens a separate pool connection. A 10-item cart opens 10 sequential connections just for stock checks, consuming 20% of the pool for a single user.
- **Symptom in logs:** Multiple sequential `Stock check passed` log entries per request.
- **Fix:** Batch all product IDs into a single query: `SELECT product_id, stock_count FROM inventory WHERE product_id = ANY($1)`

### CHECKOUT-112 — No Retry/Non-Retry Signal to Client (P1)
- **Location:** `src/main.py:205` (bare `except Exception`)
- **Problem:** All errors — transient (`DB_POOL_EXHAUSTED`, `CART_LOCK_TIMEOUT`) and permanent (`Insufficient stock`) — return `status=500`. Client has no way to know whether to retry or not.
- **Fix:**
  - `DB_POOL_EXHAUSTED` → `503` with `Retry-After` header
  - `CART_LOCK_TIMEOUT` → `503` with `Retry-After` header
  - `Insufficient stock` → `422 Unprocessable Entity`
  - Unexpected → `500`

### CHECKOUT-119 — release_lock() Worsens Pool Exhaustion During Failure (P2)
- **Location:** `src/main.py:211` (`release_lock()` inside except block)
- **Problem:** When `persist_checkout_session()` fails due to pool exhaustion, the except block calls `release_lock()` which itself calls `pool.acquire()` — adding more pressure to an already exhausted pool. If `release_lock()` also fails, the cart lock is never released (feeds back into CART-887).
- **Fix:** Maintain a dedicated persistent connection for advisory lock management, outside the shared pool.

---

## Open Tickets Summary

| Ticket | Priority | Description |
|--------|----------|-------------|
| `PLAT-4421` | P0 | Pool max_size too high for shared RDS instance |
| `CART-887` | P0 | pg_advisory_xact_lock not released on crash |
| `INV-210` | P1 | Per-item DB connection in stock validation loop |
| `CHECKOUT-112` | P1 | All errors return 500, no retry signal |
| `PRICING-55` | P2 | Hardcoded tax rate, no multi-region support |
| `CHECKOUT-119` | P2 | release_lock() opens pool conn during failure path |