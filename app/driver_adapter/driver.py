import random
import time

from playwright.sync_api import Playwright

from app.config import Config


class Driver:
    def __init__(self, playwright: Playwright, config: Config):
        self.playwright = playwright
        self.config = config
        self.browser = self.playwright.chromium.launch(headless=self.config.headless)
        self.page = self.browser.new_page()

    def login(self):

        self.page.goto(self.config.server_url)

        time.sleep(random.uniform(0.5, 2.7))

        # Wpisz login znak po znaku z losowym opóźnieniem
        for _ in range(8):
            self.page.keyboard.press('Tab')
            time.sleep(random.uniform(0.1, 0.5))

        for char in self.config.user_login:
            self.page.keyboard.type(char, delay=random.uniform(150, 200))

        time.sleep(random.uniform(0.5, 2.7))

        # Wpisz hasło znak po znaku z losowym opóźnieniem
        self.page.keyboard.press('Tab')
        for char in self.config.user_password:
            self.page.keyboard.type(char, delay=random.uniform(150, 200))

        time.sleep(random.uniform(0.5, 2.7))
        self.page.keyboard.press('Enter')

        # Poczekaj na załadowanie strony po logowaniu
        self.page.wait_for_load_state('networkidle')

        return self.page

    def stop(self):
        self.browser.close()
