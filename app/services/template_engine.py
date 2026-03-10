from app.logging_config import get_logger

logger = get_logger("template-engine")


def render_cart(cart: dict, show_checkout: bool):
    logger.info("Rendering SauceDemo cart page template version=v1.13.0")
    logger.info("Template path: /templates/cart.html")

    html = '<div id="cart_contents_container" class="cart_contents_container">'
    html += '<div><div class="header_label"><div class="title">Your Cart</div></div>'
    html += '<div class="cart_list">'
    html += '<div class="cart_item"><div class="cart_quantity">1</div><div class="cart_item_label">'
    html += '<div class="inventory_item_name">Sauce Labs Backpack</div>'
    html += '<div class="inventory_item_desc">carry.allTheThings() with the sleek, streamlined Sly Pack</div>'
    html += '<div class="inventory_item_price">$29.99</div>'
    html += '</div></div></div>'
    
    html += '<div class="cart_footer">'
    html += '<button class="btn btn_secondary back btn_medium" data-test="continue-shopping" id="continue-shopping" name="continue-shopping">Continue Shopping</button>'
    
    if show_checkout:
        logger.info("Rendering checkout button with attributes: id='checkout', data-test='checkout', class='btn btn_action btn_medium checkout_button'")
        html += '<button class="btn btn_action btn_medium checkout_button" data-test="checkout" id="checkout" name="checkout">Checkout</button>'
    else:
        logger.warning(
            "Skipping component <CheckoutButton id='checkout' /> due to feature flag ENABLE_CHECKOUT_BUTTON=false"
        )
        logger.error(
            "CRITICAL: Checkout button NOT rendered in DOM - element with id='checkout' will not exist"
        )
    
    html += '</div></div></div>'
    
    logger.info(f"Cart page rendered successfully. Checkout button present in DOM: {show_checkout}")

    return {
        "cart": cart,
        "checkout_visible": show_checkout,
        "html_rendered": html,
        "page": "cart",
        "url": "https://www.saucedemo.com/cart.html"
    }


def render_checkout_step_one():
    logger.info("Rendering SauceDemo checkout step one template version=v1.13.0")
    logger.info("Template path: /templates/checkout-step-one.html")
    
    html = '<div id="checkout_info_container" class="checkout_info_container">'
    html += '<div class="header_label"><div class="title">Checkout: Your Information</div></div>'
    html += '<div class="checkout_info">'
    html += '<form>'
    html += '<div class="checkout_info_wrapper">'
    html += '<input class="input_error form_input" placeholder="First Name" type="text" data-test="firstName" id="first-name" name="firstName" value="">'
    html += '<input class="input_error form_input" placeholder="Last Name" type="text" data-test="lastName" id="last-name" name="lastName" value="">'
    html += '<input class="input_error form_input" placeholder="Zip/Postal Code" type="text" data-test="postalCode" id="postal-code" name="postalCode" value="">'
    html += '</div>'
    html += '<div class="checkout_buttons">'
    html += '<button class="btn btn_secondary back btn_medium cart_cancel_link" data-test="cancel" id="cancel" name="cancel">Cancel</button>'
    html += '<input type="submit" class="submit-button btn btn_primary cart_button btn_action" data-test="continue" id="continue" name="continue" value="Continue">'
    html += '</div>'
    html += '</form>'
    html += '</div></div>'
    
    logger.info("Checkout step one page rendered with form fields: first-name, last-name, postal-code")
    
    return {
        "html_rendered": html,
        "page": "checkout_step_one",
        "url": "https://www.saucedemo.com/checkout-step-one.html"
    }