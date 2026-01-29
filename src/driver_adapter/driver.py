import logging
import random
from typing import List, Tuple

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
        self.login()

    def login(self) -> None:
        logger.info("Logging in...")

        self.page.goto(self.config.server_url)

        self.page.fill('input[name="name"]', self.config.user_login)
        self.page.fill('input[name="password"]', self.config.user_password)

        self.page.keyboard.press('Tab')
        for char in self.config.user_password:
            self.page.keyboard.type(char, delay=random.uniform(150, 200))

        self.page.wait_for_load_state('networkidle')

        logger.info("logged in.")

    def stop(self) -> None:
        self.browser.close()

    def navigate(self, path: str) -> None:
        """Navigate to a path on the configured server and wait for load.

        This is the single public navigation method used throughout the codebase.
        """
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.config.server_url}{path}"

        # Log where we're navigating to for easier tracing
        logger.debug(f"Navigating to: {url}")

        self.page.goto(url)
        self.page.wait_for_load_state('networkidle')

    def get_html(self, dorf: str) -> str:
        self.navigate(f"/{dorf}.php")
        return self.page.content()

    def navigate_to_village(self, id: int) -> None:
        self.navigate(f"/dorf1.php?newdid={id}")

    def refresh(self) -> None:
        self.page.reload()

    def get_village_inner_html(self, id: int) -> Tuple[str, str]:
        self.navigate_to_village(id)
        dorf1: str = self.get_html("dorf1")
        dorf2: str = self.get_html("dorf2")

        return dorf1, dorf2

    def get_hero_attributes_html(self) -> str:
        """Navigate to hero attributes page and return its HTML."""
        self.navigate("/hero/attributes")
        return self.page.content()

    def get_hero_inventory_html(self) -> str:
        """Navigate to hero inventory page and return its HTML."""
        self.navigate("/hero/inventory")
        return self.page.content()

    # --- Helper methods refactored out of complex operations ---
    def _safe_wait(self, timeout: int = 3000) -> None:
        """Call wait_for_load_state but swallow exceptions for tolerant behavior."""
        try:
            self.page.wait_for_load_state('networkidle', timeout=timeout)
        except Exception:
            # Non-fatal: we continue even if waiting fails
            pass

    def _click_first_visible(self, selectors: List[str]) -> bool:
        """Try selectors in order and click the first visible element found.

        Returns True if an element was found (even if the click raised), False otherwise.
        """
        for sel in selectors:
            try:
                locator = self.page.locator(sel).first
                if locator.count() and locator.is_visible():
                    try:
                        locator.click()
                        # success is expected and noisy; keep silent to reduce log volume
                        return True
                    except Exception:
                        # Click failed but element exists; record the selector for diagnostics
                        logger.debug(f"Element found but click failed for selector: {sel}")
                        return True
            except Exception:
                continue
        return False

    def _click_all_visible(self, selectors: List[str]) -> int:
        """Attempt to click all visible elements matching each selector.

        Returns the number of successful click attempts (approximate).
        """
        clicks = 0
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
                        # Ignore click failures for individual elements
                        logger.debug(f"Click failed for element matched by selector: {sel}")
                        continue
            except Exception:
                continue
        return clicks

    def _click_explore_button(self) -> bool:
        """Find and click the Explore button on the hero page. Returns True if clicked."""
        explore_selector = "button.textButtonV2.buttonFramed.rectangle.withText.green"
        try:
            locator = self.page.locator(explore_selector).first
            if not (locator.count() and locator.is_visible()):
                return False
            locator.click()
            # success is expected; avoid noisy logs
            return True
        except Exception:
            logger.debug(f"Failed to click explore/adventure button (selector={explore_selector})")
            return False

    def _click_questmaster_if_present(self) -> None:
        """Attempt to click questmaster button if present; swallow any failure."""
        try:
            qm = self.page.locator("#questmasterButton").first
            if qm.count() and qm.is_visible():
                qm.click()
                logger.info("Clicked questmaster button")
                self._safe_wait()
        except Exception:
            logger.debug("Questmaster button not clickable or not present")

    # --- Public high-level actions ---
    def start_hero_adventure(self) -> bool:
        """Navigate to hero adventures and attempt to start an adventure.

        Returns True when the adventure was started or when the UI indicates success,
        False when the initial explore button is not present or clicking it failed.
        """
        try:
            self.navigate("/hero/adventures")
        except Exception:
            logger.debug("Failed to navigate to /hero/adventures")
            return False

        # Click Explore; fail if not clicked
        if not self._click_explore_button():
            logger.debug("Explore button not found or not visible")
            return False

        # Allow UI to update and try continue buttons
        self._safe_wait()
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

        if self._click_first_visible(continue_selectors):
            return True

        # If no Continue found, accept arrival as success
        try:
            current_url = self.page.url
            if "/hero/adventures" in current_url:
                logger.debug("Arrived at /hero/adventures after clicking explore (no explicit continue needed)")
                return True
        except Exception:
            pass

        logger.debug("Explore clicked but no continue button found; returning success because explore was clicked")
        return True

    def claim_quest_rewards(self, page_html: str) -> int:
        """If rewards are available according to a scan, open dialogs and click Collect controls.

        Returns number of collect clicks attempted. Tolerant to UI differences and failures.
        """
        try:
            from src.scan_adapter.scanner import is_reward_available
        except Exception:
            return 0

        try:
            if not is_reward_available(page_html):
                return 0
        except Exception:
            return 0

        # Attempt questmaster click separately to reduce complexity
        self._click_questmaster_if_present()

        collect_selectors = [
            "button:has-text('Collect')",
            "button:has-text('collect')",
            "a:has-text('Collect')",
            "a:has-text('collect')",
            "text=Collect",
            "text=collect",
        ]

        clicks = self._click_all_visible(collect_selectors)
        return clicks

    def allocate_hero_attributes(self, points_to_allocate: int) -> None:
        target = DEFAULT_ATTRIBUTE_POINT_TYPE

        self.navigate('/hero/attributes')
        self.page.wait_for_selector('div.heroAttributes', timeout=3000)

        buttons_selector = "button.textButtonV2.buttonFramed.plus.rectangle.withIcon.green, [role=\"button\"].textButtonV2.buttonFramed.plus.rectangle.withIcon.green"
        buttons = self.page.locator(buttons_selector)
        button = buttons.nth(target.value - 1)

        for _ in range(points_to_allocate):
            button.click()

        save_btn = self.page.locator('#savePoints').first
        if save_btn.count() and save_btn.is_visible():
            save_btn.click()

    def claim_daily_quests(self) -> None:
        """Click the daily quests anchor and collect rewards if present."""
        try:
            self.page.wait_for_selector('#navigation a.dailyQuests', timeout=1000)
            locator = self.page.locator('#navigation a.dailyQuests').first
            if locator.count() and locator.is_visible():
                try:
                    locator.click()
                    # avoid noisy success logs
                except Exception:
                    logger.debug('dailyQuests anchor found but click failed')

            # Try to click the initial Collect rewards control if present
            collect_rewards_selectors = [
                'button.collectRewards',
                "button.textButtonV2.buttonFramed.collectRewards",
                "button:has-text('Collect rewards')",
                "text=Collect rewards",
            ]

            self._click_first_visible(collect_rewards_selectors)

            # After that, attempt final Collect buttons
            final_collect_selectors = [
                "button.collect",
                "button.collectable",
                "button:has-text('Collect')",
                "button.textButtonV2.buttonFramed.collect",
                "button.textButtonV2.buttonFramed.collect.collectable",
            ]

            self._click_all_visible(final_collect_selectors)

        except Exception:
            # Swallow exceptions to maintain tolerant UI behavior
            logger.debug('claim_daily_quests encountered an error')
