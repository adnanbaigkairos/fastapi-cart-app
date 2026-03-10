from app.logging_config import get_logger
import asyncio

logger = get_logger("cart-service")


async def get_cart(user_id: str):
    logger.info(f"Fetching SauceDemo cart for user_id={user_id}")
    logger.info("Querying cart database: SELECT * FROM carts WHERE user_id=?")
    await asyncio.sleep(0.05)

    cart = {
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
    }

    logger.info(f"Cart retrieved successfully: items={cart['items']} total=${cart['total']}")
    return cart