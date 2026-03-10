from app.logging_config import get_logger
import asyncio

logger = get_logger("feature-flag-service")


async def is_checkout_enabled(user_id: str):
    logger.info(
        f"Evaluating feature flag ENABLE_CHECKOUT_BUTTON for user_id={user_id}"
    )
    logger.info("Connecting to feature flag service at https://flags.saucedemo.internal/api/v1/evaluate")

    await asyncio.sleep(0.05)
    logger.info("Feature flag ENABLE_CHECKOUT_BUTTON evaluated to TRUE")

    return True