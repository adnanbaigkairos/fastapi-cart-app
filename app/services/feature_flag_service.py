from app.logging_config import get_logger
import asyncio

logger = get_logger("feature-flag-service")


async def is_checkout_enabled(user_id: str):
    logger.info(
        f"Evaluating feature flag ENABLE_CHECKOUT_BUTTON for user_id={user_id}"
    )
    logger.info("Connecting to feature flag service at https://flags.saucedemo.internal/api/v1/evaluate")

    await asyncio.sleep(2)

    logger.error("Feature flag service timeout after 2000ms")
    logger.error("Failed to retrieve feature flag value from remote service")
    logger.warning("This timeout will cause checkout button to NOT be rendered in cart page DOM")
    raise TimeoutError("Feature flag service timeout")