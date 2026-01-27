import logging
import random

from playwright.sync_api import Playwright

from src.config import Config
from src.core.model.model import DEFAULT_ATTRIBUTE_POINT_TYPE

logger = logging.getLogger(__name__)


class Driver:
    def __init__(self, playwright: Playwright, config: Config):
        self.playwright = playwright
        self.config = config
        self.browser = self.playwright.chromium.launch(headless=self.config.headless)
        self.page = self.browser.new_page()

    def login(self):
        logger.info("Logging in...")

        self.page.goto(self.config.server_url)

        self.page.fill('input[name="name"]', self.config.user_login)
        self.page.fill('input[name="password"]', self.config.user_password)

        self.page.keyboard.press('Tab')
        for char in self.config.user_password:
            self.page.keyboard.type(char, delay=random.uniform(150, 200))

        self.page.keyboard.press('Enter')

        self.page.wait_for_load_state('networkidle')

        logger.info("logged in.")

    def stop(self):
        self.browser.close()

    def _navigate(self, path: str) -> None:
        """Internal helper: navigate to a path on the configured server and wait for load.

        `path` may start with '/' (recommended) or be a relative path without leading slash.
        """
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.config.server_url}{path}"

        # Log where we're navigating to for easier tracing
        logger.debug(f"Navigating to: {url}")

        self.page.goto(url)
        self.page.wait_for_load_state('networkidle')

    def get_html(self, dorf: str):
        self._navigate(f"/{dorf}.php")
        return self.page.content()

    def navigate_to_village(self, id):
        self._navigate(f"/dorf1.php?newdid={id}")

    def refresh(self):
        self.page.reload()

    def get_village_inner_html(self, id: int) -> tuple[str, str]:
        self.navigate_to_village(id)
        dorf1: str = self.get_html("dorf1")
        dorf2: str = self.get_html("dorf2")

        return dorf1, dorf2

    def get_hero_attributes_html(self) -> str:
        """Navigate to hero attributes page and return its HTML."""
        self._navigate("/hero/attributes")
        return self.page.content()

    def get_hero_inventory_html(self) -> str:
        """Navigate to hero inventory page and return its HTML."""
        self._navigate("/hero/inventory")
        return self.page.content()

    def start_hero_adventure(self) -> bool:
        """Navigate to hero attributes/adventures and start an adventure.

        Steps:
        1. Open hero attributes page and click the green "explore" (adventure) button.
        2. Wait for the adventures view/modal to appear and click the "continue" button.
        """

        # Open hero attributes where the green explore button typically lives
        try:
            self._navigate("/hero/adventures")
        except Exception:
            logger.debug("Failed to navigate to /hero/adventures")
            return False

        # Use single exact selector for Explore button (no list or loop)
        sel = "button.textButtonV2.buttonFramed.rectangle.withText.green"
        try:
            locator = self.page.locator(sel).first
            if not (locator.count() and locator.is_visible()):
                logger.debug("Explore button not found or not visible")
                return False
            locator.click()
            logger.info(f"Clicked explore/adventure button using selector: {sel}")
        except Exception:
            logger.debug("Failed to click explore/adventure button")
            return False

        # After clicking explore, either a new page is loaded or a modal/window appears.
        # Wait briefly for UI to update, then attempt to click the 'continue' control.
        try:
            # allow some time for navigation/modal
            self.page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            # non-fatal, continue to look for button
            pass

        # Prioritize the exact observed Continue button selector
        continue_selectors = [
            "button.textButtonV2.buttonFramed.continue.rectangle.withText.green",
            "text=Continue",
            "button.continue",
            "a.continue",
            "button.button.green",
            "a.button.green",
            "button:has-text('Continue')",
            "a:has-text('Continue')",
        ]

        for sel in continue_selectors:
            try:
                locator = self.page.locator(sel).first
                if locator.count() and locator.is_visible():
                    try:
                        locator.click()
                        logger.info(f"Clicked continue button using selector: {sel}")
                        return True
                    except Exception:
                        # click failed, but we already clicked explore; consider this success
                        logger.debug(f"Continue button found but click failed for selector: {sel}")
                        return True
            except Exception:
                continue

        # If we couldn't find a continue button, consider the explore click successful
        # if we ended up on the adventures page (URL contains /hero/adventures) or if an
        # adventures view seems present.
        try:
            current_url = self.page.url
            if "/hero/adventures" in current_url:
                logger.info("Arrived at /hero/adventures after clicking explore (no explicit continue needed)")
                return True
        except Exception:
            pass

        logger.debug("Explore clicked but no continue button found; returning success because explore was clicked")
        return True

    def claim_quest_rewards(self, page_html: str) -> int:
        """If the quest master reward is available on the provided page HTML,
        click the quest master button and then click all elements that allow
        collecting rewards (buttons/links labeled 'Collect' or 'collect').

        Returns the number of collect clicks attempted.
        The method is tolerant and will swallow exceptions to avoid breaking
        scanning flow if the UI doesn't match exactly.
        """
        try:
            # Import scanner helper locally to avoid top-level coupling during tests
            from src.scan_adapter.scanner import is_reward_available
        except Exception:
            return 0

        try:
            if not is_reward_available(page_html):
                return 0
        except Exception:
            # If detection fails, be conservative and do nothing
            return 0

        clicks = 0
        try:
            # Try clicking the questmaster button if present on the current page
            try:
                qm = self.page.locator("#questmasterButton").first
                if qm.count() and qm.is_visible():
                    qm.click()
                    logger.info("Clicked questmaster button")
                    # wait for tasks page to load
                    try:
                        self.page.wait_for_load_state('networkidle', timeout=3000)
                    except Exception:
                        pass
            except Exception:
                logger.debug("Questmaster button not clickable or not present")

            # Now attempt to click all elements that contain text 'Collect' (case variants)
            selectors = [
                "button:has-text('Collect')",
                "button:has-text('collect')",
                "a:has-text('Collect')",
                "a:has-text('collect')",
                "text=Collect",
                "text=collect",
            ]

            for sel in selectors:
                try:
                    loc = self.page.locator(sel)
                    count = loc.count()
                    for i in range(count):
                        el = loc.nth(i)
                        try:
                            if el.is_visible():
                                el.click()
                                clicks += 1
                        except Exception:
                            # ignore click failures for individual elements
                            continue
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"claim_quest_rewards_if_available failed: {e}")

        return clicks

    def allocate_hero_attributes(self, points_to_allocate: int) -> None:
        target = DEFAULT_ATTRIBUTE_POINT_TYPE

        self._navigate('/hero/attributes')
        self.page.wait_for_selector('div.heroAttributes', timeout=3000)

        buttons_selector = "button.textButtonV2.buttonFramed.plus.rectangle.withIcon.green, [role=\"button\"].textButtonV2.buttonFramed.plus.rectangle.withIcon.green"
        buttons = self.page.locator(buttons_selector)
        button = buttons.nth(target - 1)

        for _ in range(points_to_allocate):
            button.click()

        save_btn = self.page.locator('#savePoints').first
        if save_btn.count() and save_btn.is_visible():
            save_btn.click()
