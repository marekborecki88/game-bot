import logging
import random
from typing import Iterable

from playwright.sync_api import Playwright, Locator

from src.config.config import DriverConfig
from src.core.bot import HERO_INVENTORY, CLOSE_CONTENT_BUTTON_SELECTOR, RESOURCE_TO_CLASS_MAP
from src.core.protocols.driver_protocol import DriverProtocol
from src.core.model.model import Resources

RESOURCE_TRANSFER_SUBMIT_SELECTOR = 'button.withText.green'

RESOURCE_TRANSFER_INPUT_SELECTOR = 'input[inputmode="numeric"]'

logger = logging.getLogger(__name__)


class Driver(DriverProtocol):
    def __init__(self, playwright: Playwright, driver_config: DriverConfig):
        self.playwright = playwright
        self.config = driver_config
        self.browser = self.playwright.chromium.launch(headless=self.config.headless)
        self.page = self.browser.new_page()
        self.login()

    def login(self) -> None:
        self.page.goto(self.config.server_url)

        self.page.wait_for_load_state('networkidle')

        self.page.fill('input[name="name"]', self.config.user_login)
        self.page.fill('input[name="password"]', self.config.user_password)

        # move mouse to random position within login button and click
        login_button: Locator = self.page.locator('button[type="submit"]').first
        box = login_button.bounding_box()
        if box:
            x = box["x"] + random.uniform(0, box["width"])
            y = box["y"] + random.uniform(0, box["height"])
            self.page.mouse.move(x, y)
            self.page.mouse.click(x, y)

        #wait
        self.sleep(5)

        self.page.wait_for_load_state('networkidle')

        logger.info("Successfully logged in.")

    def stop(self) -> None:
        self.browser.close()

    def navigate(self, path: str) -> None:
        """Navigate to a path on the configured server and wait for load.

        This is the single public navigation method used throughout the codebase.
        """
        url = f"{self.config.server_url}{path}"

        # Log where we're navigating to for easier tracing
        logger.debug(f"Navigating to: {url}")

        self.page.goto(url)
        self.page.wait_for_load_state('networkidle')

    def get_html(self, path: str) -> str:
        self.navigate(path)
        return self.page.content()

    def navigate_to_village(self, village_id: int) -> None:
        self.navigate(f"/dorf1.php?newdid={village_id}")

    def refresh(self) -> None:
        self.page.reload()

    def get_village_inner_html(self, village_id: int) -> tuple[str, str]:
        self.navigate_to_village(village_id)
        dorf1: str = self.get_html("/dorf1.php")
        dorf2: str = self.get_html("/dorf2.php")

        return dorf1, dorf2

    # --- Public primitives only ---
    def click(self, selector: str) -> bool:
        """Click first element matching selector if visible; return True on click."""
        try:
            locator = self.page.locator(selector).first
            if locator.count() and locator.is_visible():
                try:
                    locator.click()
                    return True
                except Exception:
                    logger.debug(f"Click found element but click failed for selector: {selector}")
                    return True
        except Exception:
            pass
        return False

    def click_first(self, selectors: Iterable[str]) -> bool:
        """Try selectors in order and click the first visible element found."""
        for sel in selectors:
            try:
                locator = self.page.locator(sel).first
                if locator.count() and locator.is_visible():
                    try:
                        locator.click()
                        return True
                    except Exception:
                        logger.debug(f"Element found but click failed for selector: {sel}")
                        return True
            except Exception:
                continue
        return False

    def click_all(self, selectors: Iterable[str]) -> int:
        """Click all visible elements matching provided selectors."""
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
                        logger.debug(f"Click failed for element matched by selector: {sel}")
                        continue
            except Exception:
                continue
        return clicks

    def wait_for_load_state(self, timeout: int = 3000) -> None:
        """Wait for page to settle; swallow non-fatal errors."""
        try:
            self.page.wait_for_load_state('networkidle', timeout=timeout)
        except Exception:
            pass

    def current_url(self) -> str:
        return self.page.url


    def transfer_resources_from_hero(self, support: Resources):
        self.navigate(HERO_INVENTORY)

        for item_id, amount in vars(support).items():
            if amount > 0:
                self.transfer_resource(amount, item_id)

        logger.info(f"Transferred {support} from hero inventory.")
        self.click(CLOSE_CONTENT_BUTTON_SELECTOR)


    def transfer_resource(self, amount, item_id: str):
        cls = RESOURCE_TO_CLASS_MAP.get(item_id)
        selector = f"item {cls} none"
        logger.debug(f"Try to click {selector}")
        self._wait_for_selector_and_click_by_class(selector)
        # wait for input to appear
        self.wait_for_selector(RESOURCE_TRANSFER_INPUT_SELECTOR, timeout=2000)
        # self._fill_input('input[inputmode="numeric"]', str(amount))
        self.page.fill(RESOURCE_TRANSFER_INPUT_SELECTOR, str(amount))
        self.click(RESOURCE_TRANSFER_SUBMIT_SELECTOR)

    def _wait_for_selector_and_click_by_class(self, class_name: str) -> bool:
        self.wait_for_selector(class_name)
        return self.page.evaluate(
            """
                (cls) => {
                    const el = document.getElementsByClassName(cls)[0];
                    if (el) {
                        el.click();
                        return true;
                    }
                    return false;
                }
            """,
            class_name,
        )

    def wait_for_selector(self, selector: str, timeout: int = 3000) -> bool:
        try:
            self.page.wait_for_selector(selector.replace(" ", "."), timeout=timeout)
            return True
        except Exception:
            return False

    def click_nth(self, selector: str, index: int) -> bool:
        try:
            locs = self.page.locator(selector)
            if locs.count() > index:
                el = locs.nth(index)
                if el.is_visible():
                    try:
                        el.click()
                        return True
                    except Exception:
                        logger.debug(f"click_nth failed for selector={selector} index={index}")
                        return False
        except Exception:
            pass
        return False

    def wait_for_selector_and_click(self, selector: str, timeout: int = 3000) -> None:
        self.wait_for_selector(selector, timeout=timeout)
        self.click(selector)

    def catch_full_classes_by_selector(self, selector: str) -> str:
        return self.page.locator(selector).first.get_attribute("class") or ""

    def sleep(self, seconds: int) -> None:
        self.page.wait_for_timeout(seconds * 1000)

    def is_visible(self, selector: str) -> bool:
        try:
            locator = self.page.locator(selector).first
            return locator.count() > 0 and locator.is_visible()
        except Exception:
            return False