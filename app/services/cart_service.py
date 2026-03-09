from app.logging_config import get_logger
import asyncio

logger = get_logger("cart-service")


async def get_cart(user_id: str):
    logger.info(f"Fetching cart for user_id={user_id}")
    await asyncio.sleep(0.05)

    cart = {
        "items": 1,
        "total": 29.99
    }

    logger.info(f"Cart response items={cart['items']} total={cart['total']}")
    return cart