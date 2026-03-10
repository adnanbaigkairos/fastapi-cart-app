from app.logging_config import get_logger

logger = get_logger("page-objects")


class CartPageLocators:
    CHECKOUT_BUTTON_CORRECT = "By.id: checkout"
    CHECKOUT_BUTTON_XPATH_CORRECT = "By.xpath: //button[@id='checkout']"
    CHECKOUT_BUTTON_CSS_CORRECT = "By.cssSelector: button[data-test='checkout']"
    
    CHECKOUT_BUTTON_CORRUPTED_ID = "By.id: checking out"
    CHECKOUT_BUTTON_CORRUPTED_NAME = "By.name: checking out"
    CHECKOUT_BUTTON_CORRUPTED_XPATH_1 = "By.xpath: //button[@idqksm='checksalxmout']"
    CHECKOUT_BUTTON_CORRUPTED_XPATH_2 = "By.xpath: //bukqsnmtton[@namkasne='checking out']"
    
    CONTINUE_SHOPPING = "By.id: continue-shopping"


class CheckoutStepOneLocators:
    FIRST_NAME_CORRECT = "By.id: first-name"
    FIRST_NAME_XPATH_CORRECT = "By.xpath: //input[@id='first-name']"
    FIRST_NAME_CSS_CORRECT = "By.cssSelector: input[data-test='firstName']"
    
    LAST_NAME_CORRECT = "By.id: last-name"
    POSTAL_CODE_CORRECT = "By.id: postal-code"
    CONTINUE_BUTTON = "By.id: continue"
    CANCEL_BUTTON = "By.id: cancel"


class LocatorRepository:
    def __init__(self):
        self.cart_page_locators = {
            "checkout_button": CartPageLocators.CHECKOUT_BUTTON_CORRUPTED_ID,
            "continue_shopping": CartPageLocators.CONTINUE_SHOPPING
        }
        
        self.checkout_step_one_locators = {
            "first_name": CheckoutStepOneLocators.FIRST_NAME_CORRECT,
            "last_name": CheckoutStepOneLocators.LAST_NAME_CORRECT,
            "postal_code": CheckoutStepOneLocators.POSTAL_CODE_CORRECT,
            "continue": CheckoutStepOneLocators.CONTINUE_BUTTON
        }
        
        logger.warning(
            f"Locator repository initialized with CORRUPTED checkout button locator: {self.cart_page_locators['checkout_button']}"
        )
        logger.info(
            f"Correct locator should be: {CartPageLocators.CHECKOUT_BUTTON_CORRECT}"
        )
    
    def get_locator(self, page: str, element: str):
        if page == "cart":
            return self.cart_page_locators.get(element)
        elif page == "checkout_step_one":
            return self.checkout_step_one_locators.get(element)
        return None
    
    def get_all_fallback_locators(self, element_name: str):
        if element_name == "checkout_button":
            return [
                CartPageLocators.CHECKOUT_BUTTON_CORRUPTED_XPATH_1,
                CartPageLocators.CHECKOUT_BUTTON_CORRUPTED_XPATH_2,
                "By.xpath: //button[@clasqskns='btn btaknxn_action btn_medium checking out_button ']",
                "By.xpath: //buqksnqasksnxtton[contains(text(), 'checking out')]",
                "By.cssSelector: [id='checking out']",
                "By.cssSelector: buttonsxs[id='checking out']",
                "By.cssSelector: #checking out",
                "By.cssSelector: button[id='checking out']",
                "By.cssSelector: button[name='checking out']",
                "By.cssSelector: button[class='btn btn_akxnction btn_medium checking out_button ']",
                "By.id: checking outtttt",
                CartPageLocators.CHECKOUT_BUTTON_CORRUPTED_NAME
            ]
        elif element_name == "first_name":
            return [
                CheckoutStepOneLocators.FIRST_NAME_XPATH_CORRECT,
                "By.xpath: //input[@name='firstName']",
                "By.xpath: //input[@placeholder='First Name']",
                CheckoutStepOneLocators.FIRST_NAME_CSS_CORRECT,
                CheckoutStepOneLocators.FIRST_NAME_CORRECT,
                "By.name: firstName"
            ]
        return []


locator_repo = LocatorRepository()
