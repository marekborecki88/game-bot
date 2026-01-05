import random
import time

from playwright.sync_api import Playwright

from app.config import Config


class Driver:
    def __init__(self, playwright: Playwright, config: Config):
        self.playwright = playwright
        self.config = config
        self.browser = self.playwright.chromium.launch(headless=self.config.headless)
        self.page = None

    def login(self):
        # I don't like this line
        self.page = self.browser.new_page()

        self.page.goto(self.config.server_url)

        self.page.fill('input[name="name"]', self.config.user_login)
        self.page.fill('input[name="password"]', self.config.user_password)

        time.sleep(random.uniform(1, 3))

        self.page.click('button[type="submit"]')

        return self.page

    def stop(self):
        self.browser.close()
