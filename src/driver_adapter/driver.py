import logging
import random

from playwright.sync_api import Playwright

from src.config import Config

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
