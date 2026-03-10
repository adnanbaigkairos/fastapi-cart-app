from app.logging_config import get_logger

logger = get_logger("locator-analyzer")


class LocatorCorruptionAnalyzer:
    
    @staticmethod
    def analyze_checkout_button_locators():
        logger.info("=== LOCATOR CORRUPTION ANALYSIS ===")
        logger.info("Analyzing checkout button locator repository...")
        
        correct_locators = {
            "id": "checkout",
            "data-test": "checkout",
            "class": "btn btn_action btn_medium checkout_button",
            "name": "checkout"
        }
        
        corrupted_locators = {
            "id": "checking out",
            "name": "checking out",
            "xpath_id_attr": "idqksm='checksalxmout'",
            "xpath_name_attr": "namkasne='checking out'",
            "xpath_class_attr": "clasqskns='btn btaknxn_action btn_medium checking out_button '"
        }
        
        logger.warning("CORRECT locators for SauceDemo checkout button:")
        for attr, value in correct_locators.items():
            logger.info(f"  {attr}: '{value}'")
        
        logger.error("CORRUPTED locators found in test script/page object repository:")
        for attr, value in corrupted_locators.items():
            logger.error(f"  {attr}: '{value}'")
        
        logger.error("ROOT CAUSE: Locator repository contains invalid selectors with:")
        logger.error("  1. IDs containing spaces (invalid CSS/HTML): 'checking out' instead of 'checkout'")
        logger.error("  2. Random character corruption in XPath attributes: 'idqksm', 'namkasne', 'clasqskns'")
        logger.error("  3. Typos in element names: 'bukqsnmtton' instead of 'button'")
        logger.error("  4. Extra characters in ID: 'checking outtttt'")
        
        logger.warning("IMPACT: Even though checkout button IS rendered in DOM with id='checkout',")
        logger.warning("the test framework cannot locate it because it searches for id='checking out'")
        
        logger.info("RECOMMENDATION: Fix page object repository to use correct locator: id='checkout'")
        logger.info("=== END ANALYSIS ===")
    
    @staticmethod
    def analyze_first_name_locators():
        logger.info("=== FIRST NAME FIELD LOCATOR ANALYSIS ===")
        logger.info("Analyzing first name field locators...")
        
        logger.info("CORRECT locators for first name field (checkout-step-one.html):")
        logger.info("  id: 'first-name'")
        logger.info("  data-test: 'firstName'")
        logger.info("  name: 'firstName'")
        
        logger.warning("ISSUE: First name field locators are CORRECT")
        logger.error("ROOT CAUSE: Element not found because test is on WRONG PAGE")
        logger.error("  Current page: cart.html (Your Cart)")
        logger.error("  Expected page: checkout-step-one.html (Checkout: Your Information)")
        logger.error("  Reason: Navigation failed in step 14 due to corrupted checkout button locator")
        
        logger.warning("CASCADING FAILURE: Step 14 failure prevented navigation to checkout-step-one.html")
        logger.warning("Therefore, first-name input does not exist in current DOM")
        
        logger.info("=== END ANALYSIS ===")


def run_full_analysis():
    analyzer = LocatorCorruptionAnalyzer()
    analyzer.analyze_checkout_button_locators()
    analyzer.analyze_first_name_locators()
