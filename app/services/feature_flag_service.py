from app.logging_config import get_logger
import asyncio

logger = get_logger("feature-flag-service")


async def is_checkout_enabled(user_id: str):
    logger.info(
        f"Evaluating feature flag ENABLE_CHECKOUT_BUTTON for user_id={user_id}"
    )

    # Simulate timeout
    await asyncio.sleep(2)

    logger.error("Feature flag service timeout after 2000ms")
    raise TimeoutError("Feature flag service timeout")