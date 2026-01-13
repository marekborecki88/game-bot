import random
import time

from playwright.sync_api import Playwright

from src.config import Config


class Driver:
    def __init__(self, playwright: Playwright, config: Config):
        self.playwright = playwright
        self.config = config
        self.browser = self.playwright.chromium.launch(headless=self.config.headless)
        self.page = self.browser.new_page()

    def login(self):
        print("Logging in...")

        self.page.goto(self.config.server_url)

        self.page.fill('input[name="name"]', self.config.user_login)
        self.page.fill('input[name="password"]', self.config.user_password)

        self.page.keyboard.press('Tab')
        for char in self.config.user_password:
            self.page.keyboard.type(char, delay=random.uniform(150, 200))

        self.page.keyboard.press('Enter')

        self.page.wait_for_load_state('networkidle')

        print("logged in.")
        return self.page

    def stop(self):
        self.browser.close()

    def get_html(self, dorf: str):
        self.page.goto(f"{self.config.server_url}/{dorf}.php")
        self.page.wait_for_selector(".villageList")
        return self.page.content()

    def navigate_to_village(self, id):
        pass

    def refresh(self):
        self.page.reload()
