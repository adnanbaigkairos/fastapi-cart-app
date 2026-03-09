from app.logging_config import get_logger

logger = get_logger("template-engine")


def render_cart(cart: dict, show_checkout: bool):
    logger.info("Rendering cart template version=v1.12.4")

    if not show_checkout:
        logger.warning(
            "Skipping component <CheckoutButton /> due to feature flag false"
        )

    return {
        "cart": cart,
        "checkout_visible": show_checkout
    }