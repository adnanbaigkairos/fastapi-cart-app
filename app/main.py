from fastapi import FastAPI
import time
import asyncio
from app.logging_config import get_logger
from app.services.cart_service import get_cart
from app.services.feature_flag_service import is_checkout_enabled
from app.services.template_engine import render_cart, render_checkout_step_one
from app.services.test_runner_simulator import simulate_test_execution

app = FastAPI()
logger = get_logger("web-app")


@app.get("/cart.html")
async def cart_page(user_id: str = "U10293"):
    start_time = time.time()

    logger.info("Incoming request GET /cart.html")

    cart = await get_cart(user_id)

    try:
        checkout_enabled = await is_checkout_enabled(user_id)
    except TimeoutError:
        logger.warning(
            "Feature flag ENABLE_CHECKOUT_BUTTON defaulted to false due to service failure"
        )
        logger.warning(
            "Checkout button will not be rendered for this session"
        )
        checkout_enabled = False

    response = render_cart(cart, checkout_enabled)

    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        f"Response completed GET /cart.html status=200 duration_ms={duration_ms}"
    )

    return response


@app.get("/simulate-test")
async def simulate_saucedemo_test():
    return await simulate_test_execution()


@app.get("/checkout-step-one.html")
async def checkout_step_one_page():
    logger.info("Incoming request GET /checkout-step-one.html")
    logger.warning("This page should only be accessible after successful checkout button click")
    
    response = render_checkout_step_one()
    
    logger.info("Response completed GET /checkout-step-one.html status=200")
    
    return response