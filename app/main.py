# src/main.py
import asyncpg
import uuid
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.routing import APIRouter

# ── Logger setup ────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("saucedemo")

# ── DB Pool ──────────────────────────────────────────────────────────────────
_pool = None

async def get_pool() -> asyncpg.Pool:                                              # line 14
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(                                         # line 17
            dsn="postgresql://user:password@localhost:5432/saucedemo",
            min_size=5,
            max_size=50,                                                           # line 20 — pool cap, exhaustion root cause
            command_timeout=30
        )
    return _pool

# ── Cart DB ──────────────────────────────────────────────────────────────────
async def find_cart_by_id(cart_id: str) -> dict:                                   # line 25
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM carts WHERE cart_id = $1", cart_id                      # line 29
        )
        items = await conn.fetch(
            """SELECT ci.product_id, ci.quantity, ci.unit_price as price,
               p.name FROM cart_items ci 
               JOIN products p ON ci.product_id = p.id 
               WHERE ci.cart_id = $1""", cart_id                                   # line 35
        )
        return {
            "id": row["cart_id"],
            "user_id": row["user_id"],
            "items": [dict(i) for i in items],
            "subtotal": float(row["subtotal"])
        }

async def acquire_cart_lock(cart_id: str, user_id: str, timeout_ms: int):         # line 44
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                f"SET lock_timeout = '{timeout_ms}ms';"                            # line 49
            )
            await conn.execute(
                "SELECT pg_advisory_xact_lock($1)", hash(cart_id)                  # line 52
            )
        except asyncpg.exceptions.LockNotAvailableError as e:
            logger.error({"service": "cart-db", "message": f"Failed to acquire row lock on cart_id={cart_id} — lock held by concurrent session timeout_ms={timeout_ms} error=ER_LOCK_WAIT_TIMEOUT exception={str(e)}"})
            raise RuntimeError("CART_LOCK_TIMEOUT")                                # line 56

async def release_cart_lock(cart_id: str):                                         # line 58
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT pg_advisory_unlock($1)", hash(cart_id)                         # line 62
        )

# ── Product DB ───────────────────────────────────────────────────────────────
async def get_product_stock(product_id: str) -> int:                               # line 66
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT stock_count FROM inventory WHERE product_id = $1", product_id  # line 70
        )
        return int(row["stock_count"]) if row else 0

# ── Checkout DB ──────────────────────────────────────────────────────────────
async def persist_checkout_session(session: dict):                                 # line 75
    logger.info({"service": "checkout-db", "message": f"Persisting checkout session checkout_id={session['checkout_id']} cart_id={session['cart_id']} user_id={session['user_id']}"})
    try:
        pool = await get_pool()
        async with pool.acquire(timeout=3.0) as conn:                              # line 79 — raises asyncpg.TooManyConnectionsError if pool exhausted
            await conn.execute(
                """INSERT INTO checkout_sessions
                   (checkout_id, cart_id, user_id, subtotal, tax, shipping, total, status, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, 'initiated', NOW())""",    # line 83
                session["checkout_id"], session["cart_id"], session["user_id"],
                session["subtotal"], session["tax"], session["shipping"], session["total"]
            )
    except asyncpg.TooManyConnectionsError as e:
        logger.error({"service": "checkout-db", "message": f"INSERT INTO checkout_sessions failed — connection pool exhausted active_connections=50 max_connections=50 wait_queue=12 error=POOL_EXHAUSTED checkout_id={session['checkout_id']} exception={str(e)}"})
        raise RuntimeError("DB_POOL_EXHAUSTED")                                    # line 90
    except asyncpg.PostgresError as e:
        logger.error({"service": "checkout-db", "message": f"INSERT INTO checkout_sessions failed — postgres error checkout_id={session['checkout_id']} error={str(e)}"})
        raise RuntimeError("DB_WRITE_FAILED")                                      # line 93

# ── Cart Service ─────────────────────────────────────────────────────────────
async def get_cart(cart_id: str, user_id: str) -> dict:                            # line 96
    logger.info({"service": "cart-service", "message": f"Fetching cart cart_id={cart_id} user_id={user_id}"})
    cart = await find_cart_by_id(cart_id)                                          # line 98
    logger.info({"service": "cart-service", "message": f"Cart fetched successfully cart_id={cart_id} items={len(cart['items'])} subtotal={cart['subtotal']} user_id={user_id}"})
    return cart

async def lock_cart(cart_id: str, user_id: str):                                   # line 102
    logger.info({"service": "cart-service", "message": f"Attempting to lock cart cart_id={cart_id} user_id={user_id}"})
    await acquire_cart_lock(cart_id, user_id, timeout_ms=5000)                     # line 104
    logger.info({"service": "cart-service", "message": f"Cart locked successfully cart_id={cart_id} user_id={user_id}"})

async def release_lock(cart_id: str, user_id: str):                                # line 108
    logger.warning({"service": "cart-service", "message": f"Releasing cart lock due to checkout failure cart_id={cart_id} user_id={user_id}"})
    await release_cart_lock(cart_id)                                               # line 110
    logger.info({"service": "cart-service", "message": f"Cart lock released cart_id={cart_id} user_id={user_id} cart restored to open state"})

# ── Inventory Service ────────────────────────────────────────────────────────
async def validate_stock(cart: dict):                                              # line 114
    logger.info({"service": "inventory-service", "message": f"Validating stock for cart_id={cart['id']} item_count={len(cart['items'])} user_id={cart['user_id']}"})
    for item in cart["items"]:                                                     # line 116
        stock = await get_product_stock(item["product_id"])                        # line 117
        logger.info({"service": "inventory-service", "message": f"Stock check passed product_id={item['product_id']} requested={item['quantity']} available={stock}"})
        if stock < item["quantity"]:                                               # line 119
            raise RuntimeError(f"Insufficient stock for product_id={item['product_id']}")

# ── Pricing Service ──────────────────────────────────────────────────────────
TAX_RATE = 0.08                                                                    # line 123
SHIPPING_FLAT_RATE = 5.99                                                          # line 124

async def calculate_total(cart: dict, user_id: str) -> dict:                       # line 126
    logger.info({"service": "pricing-service", "message": f"Calculating order total for cart_id={cart['id']} user_id={user_id}"})
    subtotal = round(sum(i["price"] * i["quantity"] for i in cart["items"]), 2)   # line 128
    logger.info({"service": "pricing-service", "message": f"Subtotal calculated subtotal={subtotal} user_id={user_id}"})
    tax = round(subtotal * TAX_RATE, 2)                                            # line 130
    shipping = SHIPPING_FLAT_RATE                                                  # line 131
    total = round(subtotal + tax + shipping, 2)
    logger.info({"service": "pricing-service", "message": f"Order total confirmed subtotal={subtotal} tax={tax} shipping={shipping} total={total} user_id={user_id}"})
    return {"subtotal": subtotal, "tax": tax, "shipping": shipping, "total": total}

# ── Checkout Service ─────────────────────────────────────────────────────────
async def create_session(cart: dict, total: dict, user_id: str) -> dict:           # line 136
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

# ── Route ────────────────────────────────────────────────────────────────────
app = FastAPI()
router = APIRouter()

@router.post("/api/v1/checkout/init")
async def init_checkout(request: Request):                                         # line 153
    body = await request.json()
    cart_id = body.get("cart_id")
    user_id = request.state.user_id

    logger.info({"service": "web-app", "message": f"Incoming request POST /api/v1/checkout/init user_id={user_id} cart_id={cart_id}"})

    try:
        cart = await get_cart(cart_id, user_id)                                    # line 161 → src/main.py:96
        await lock_cart(cart_id, user_id)                                          # line 162 → src/main.py:102
        await validate_stock(cart)                                                 # line 163 → src/main.py:114
        total = await calculate_total(cart, user_id)                               # line 164 → src/main.py:126
        session = await create_session(cart, total, user_id)                       # line 165 → src/main.py:136
        await persist_checkout_session(session)                                    # line 166 → src/main.py:75
        return {"checkout_id": session["checkout_id"], "status": "initiated"}
    except Exception as e:
        logger.error({"service": "checkout-service", "message": str(e), "cart_id": cart_id, "user_id": user_id})
        await release_lock(cart_id, user_id)                                       # line 170 → src/main.py:108
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(router)