# src/main.py
import asyncpg
import uuid
import logging
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.routing import APIRouter

# ── Logger setup ────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("saucedemo")

# ── DB Pool ──────────────────────────────────────────────────────────────────
# KNOWN ISSUE: max_size=50 was set during initial dev for a 2-node deployment.
# Current prod runs 6 nodes × 50 = 300 potential connections against a
# Postgres RDS db.t3.medium which hard-caps at 170 max_connections.
# Under checkout traffic spikes all 50 slots per node fill instantly,
# leaving other nodes starved. Ticket: PLAT-4421 (unresolved)
# TODO: Reduce max_size to 15 per node OR migrate to PgBouncer connection pooler.
_pool = None
POOL_MIN_SIZE = 5
POOL_MAX_SIZE = 50        # ← ROOT CAUSE: too high for shared RDS instance, see above
POOL_COMMAND_TIMEOUT = 30
DB_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/saucedemo")

async def get_pool() -> asyncpg.Pool:                                              # line 24
    global _pool
    if _pool is None:
        # WARNING: No pool health check configured. If DB restarts,
        # stale connections are not evicted until command_timeout fires.
        _pool = await asyncpg.create_pool(                                         # line 29
            dsn=DB_URL,
            min_size=POOL_MIN_SIZE,
            max_size=POOL_MAX_SIZE,                                                # line 32 — exhaustion root cause
            command_timeout=POOL_COMMAND_TIMEOUT
        )
    return _pool

# ── Cart DB ──────────────────────────────────────────────────────────────────
async def find_cart_by_id(cart_id: str) -> dict:                                   # line 38
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM carts WHERE cart_id = $1", cart_id                      # line 42
        )
        items = await conn.fetch(
            """SELECT ci.product_id, ci.quantity, ci.unit_price as price,
               p.name FROM cart_items ci
               JOIN products p ON ci.product_id = p.id
               WHERE ci.cart_id = $1""", cart_id                                   # line 48
        )
        return {
            "id": row["cart_id"],
            "user_id": row["user_id"],
            "items": [dict(i) for i in items],
            "subtotal": float(row["subtotal"])
        }

# KNOWN ISSUE: pg_advisory_xact_lock is a session-level lock that is NOT
# automatically released when the transaction ends — it persists until the
# connection is closed or pg_advisory_unlock() is explicitly called.
# If release_cart_lock() is skipped due to an unhandled exception path,
# the lock will remain held until the connection is recycled by the pool,
# blocking all other checkout attempts on the same cart_id indefinitely.
# This is the cause of the "lock held by concurrent session" errors seen
# in prod — a previous failed checkout never released the lock. Ticket: CART-887
async def acquire_cart_lock(cart_id: str, user_id: str, timeout_ms: int):         # line 64
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(f"SET lock_timeout = '{timeout_ms}ms';")            # line 68
            await conn.execute(
                "SELECT pg_advisory_xact_lock($1)", hash(cart_id)                  # line 70
            )
        except asyncpg.exceptions.LockNotAvailableError as e:
            logger.error({"service": "cart-db", "message": f"Failed to acquire row lock on cart_id={cart_id} — lock held by concurrent session timeout_ms={timeout_ms} error=ER_LOCK_WAIT_TIMEOUT exception={str(e)}"})
            raise RuntimeError("CART_LOCK_TIMEOUT")                                # line 74

async def release_cart_lock(cart_id: str):                                         # line 76
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT pg_advisory_unlock($1)", hash(cart_id)                         # line 80
        )

# ── Product DB ───────────────────────────────────────────────────────────────
# NOTE: No caching layer here. Every stock check hits the DB directly.
# Under high load this becomes a hot read on the inventory table.
# Redis TTL cache was planned in INV-210 but not yet implemented.
async def get_product_stock(product_id: str) -> int:                               # line 87
    pool = await get_pool()
    async with pool.acquire() as conn:                                             # line 89 — consumes a pool connection per item in cart
        row = await conn.fetchrow(
            "SELECT stock_count FROM inventory WHERE product_id = $1", product_id  # line 91
        )
        return int(row["stock_count"]) if row else 0

# ── Checkout DB ──────────────────────────────────────────────────────────────
# CRITICAL: pool.acquire(timeout=3.0) will raise asyncpg.TooManyConnectionsError
# when all 50 pool slots are occupied. This is NOT caught upstream in init_checkout()
# as a retriable error — it surfaces as a generic 500 to the client.
# The 3.0s acquire timeout was added as a quick fix in PR #412 to avoid
# indefinite hangs, but the underlying pool exhaustion was never addressed.
# Under load: find_cart_by_id() + acquire_cart_lock() + get_product_stock() (×n items)
# each consume a separate pool connection. For a 2-item cart that is already
# 4 connections consumed before persist() is even called.
async def persist_checkout_session(session: dict):                                 # line 104
    logger.info({"service": "checkout-db", "message": f"Persisting checkout session checkout_id={session['checkout_id']} cart_id={session['cart_id']} user_id={session['user_id']}"})
    try:
        pool = await get_pool()
        async with pool.acquire(timeout=3.0) as conn:                              # line 108 — raises TooManyConnectionsError if pool exhausted
            await conn.execute(
                """INSERT INTO checkout_sessions
                   (checkout_id, cart_id, user_id, subtotal, tax, shipping, total, status, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, 'initiated', NOW())""",    # line 112
                session["checkout_id"], session["cart_id"], session["user_id"],
                session["subtotal"], session["tax"], session["shipping"], session["total"]
            )
    except asyncpg.TooManyConnectionsError as e:
        logger.error({"service": "checkout-db", "message": f"INSERT INTO checkout_sessions failed — connection pool exhausted active_connections=50 max_connections=50 wait_queue=12 error=POOL_EXHAUSTED checkout_id={session['checkout_id']} exception={str(e)}"})
        raise RuntimeError("DB_POOL_EXHAUSTED")                                    # line 119
    except asyncpg.PostgresError as e:
        logger.error({"service": "checkout-db", "message": f"INSERT INTO checkout_sessions failed — postgres error checkout_id={session['checkout_id']} error={str(e)}"})
        raise RuntimeError("DB_WRITE_FAILED")                                      # line 122

# ── Cart Service ─────────────────────────────────────────────────────────────
async def get_cart(cart_id: str, user_id: str) -> dict:                            # line 125
    logger.info({"service": "cart-service", "message": f"Fetching cart cart_id={cart_id} user_id={user_id}"})
    cart = await find_cart_by_id(cart_id)                                          # line 127 — opens pool conn #1
    logger.info({"service": "cart-service", "message": f"Cart fetched successfully cart_id={cart_id} items={len(cart['items'])} subtotal={cart['subtotal']} user_id={user_id}"})
    return cart

async def lock_cart(cart_id: str, user_id: str):                                   # line 131
    logger.info({"service": "cart-service", "message": f"Attempting to lock cart cart_id={cart_id} user_id={user_id}"})
    await acquire_cart_lock(cart_id, user_id, timeout_ms=5000)                     # line 133 — opens pool conn #2
    logger.info({"service": "cart-service", "message": f"Cart locked successfully cart_id={cart_id} user_id={user_id}"})

async def release_lock(cart_id: str, user_id: str):                                # line 137
    logger.warning({"service": "cart-service", "message": f"Releasing cart lock due to checkout failure cart_id={cart_id} user_id={user_id}"})
    await release_cart_lock(cart_id)                                               # line 139 — opens pool conn #4 (adds pressure during failure path too)
    logger.info({"service": "cart-service", "message": f"Cart lock released cart_id={cart_id} user_id={user_id} cart restored to open state"})

# ── Inventory Service ─────────────────────────────────────────────────────────
async def validate_stock(cart: dict):                                              # line 143
    logger.info({"service": "inventory-service", "message": f"Validating stock for cart_id={cart['id']} item_count={len(cart['items'])} user_id={cart['user_id']}"})
    for item in cart["items"]:                                                     # line 145
        # BUG: A new pool connection is acquired per item (line 89).
        # A cart with 10 items opens 10 sequential connections.
        # These are not batched into a single IN() query.
        # Fix: batch all product_ids into one SELECT ... WHERE product_id = ANY($1)
        stock = await get_product_stock(item["product_id"])                        # line 150 — opens pool conn #3 per item
        logger.info({"service": "inventory-service", "message": f"Stock check passed product_id={item['product_id']} requested={item['quantity']} available={stock}"})
        if stock < item["quantity"]:                                               # line 152
            raise RuntimeError(f"Insufficient stock for product_id={item['product_id']}")

# ── Pricing Service ───────────────────────────────────────────────────────────
# NOTE: TAX_RATE is hardcoded flat rate. Multi-region tax logic (PRICING-55)
# was deferred. If user region changes between cart load and checkout,
# the tax amount will be stale. No re-validation against user profile at runtime.
TAX_RATE = 0.08                                                                    # line 158 — hardcoded, not fetched from tax-service
SHIPPING_FLAT_RATE = 5.99                                                          # line 159 — no carrier API call, always flat

async def calculate_total(cart: dict, user_id: str) -> dict:                       # line 161
    logger.info({"service": "pricing-service", "message": f"Calculating order total for cart_id={cart['id']} user_id={user_id}"})
    subtotal = round(sum(i["price"] * i["quantity"] for i in cart["items"]), 2)   # line 163
    logger.info({"service": "pricing-service", "message": f"Subtotal calculated subtotal={subtotal} user_id={user_id}"})
    tax = round(subtotal * TAX_RATE, 2)                                            # line 165
    shipping = SHIPPING_FLAT_RATE                                                  # line 166
    total = round(subtotal + tax + shipping, 2)
    logger.info({"service": "pricing-service", "message": f"Order total confirmed subtotal={subtotal} tax={tax} shipping={shipping} total={total} user_id={user_id}"})
    return {"subtotal": subtotal, "tax": tax, "shipping": shipping, "total": total}

# ── Checkout Service ──────────────────────────────────────────────────────────
async def create_session(cart: dict, total: dict, user_id: str) -> dict:           # line 171
    checkout_id = f"CHK_{uuid.uuid4().hex[:5].upper()}"
    logger.info({"service": "checkout-service", "message": f"Checkout session created checkout_id={checkout_id} cart_id={cart['id']} user_id={user_id}"})
    return {
        "checkout_id": checkout_id,
        "cart_id": cart["id"],
        "user_id": user_id,
        "total": total["total"],
        "subtotal": total["subtotal"],
        "tax": total["tax"],
        "shipping": total["shipping"]
    }

# ── Route ─────────────────────────────────────────────────────────────────────
app = FastAPI()
router = APIRouter()

@router.post("/api/v1/checkout/init")
async def init_checkout(request: Request):                                         # line 187
    body = await request.json()
    cart_id = body.get("cart_id")
    user_id = request.state.user_id

    logger.info({"service": "web-app", "message": f"Incoming request POST /api/v1/checkout/init user_id={user_id} cart_id={cart_id}"})

    try:
        cart   = await get_cart(cart_id, user_id)                                  # line 195 — pool conn #1
        await    lock_cart(cart_id, user_id)                                       # line 196 — pool conn #2
        await    validate_stock(cart)                                              # line 197 — pool conn #3 per item
        total  = await calculate_total(cart, user_id)                              # line 198 — no pool conn (pure compute)
        session= await create_session(cart, total, user_id)                        # line 199 — no pool conn
        await    persist_checkout_session(session)                                 # line 200 — pool conn #4 ← fails here under load
        return {"checkout_id": session["checkout_id"], "status": "initiated"}

    except Exception as e:
        # WARNING: All exception types caught here including DB_POOL_EXHAUSTED,
        # CART_LOCK_TIMEOUT, and stock errors. No differentiation for retry logic.
        # Client always receives status=500 regardless of whether the error
        # is transient (pool exhaustion → retryable) or permanent (no stock → not retryable).
        # TODO: Distinguish HTTPException(503, retryable=True) vs HTTPException(422) by error code.
        logger.error({"service": "checkout-service", "message": str(e), "cart_id": cart_id, "user_id": user_id})
        await release_lock(cart_id, user_id)                                       # line 211 — pool conn #5 during failure (worsens pool pressure)
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(router)