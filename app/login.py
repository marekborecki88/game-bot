import random
import time
from playwright.sync_api import Playwright
from app.config import Config


def login(playwright: Playwright, config: Config):
    browser = playwright.chromium.launch(headless=config.headless)
    page = browser.new_page()

    page.goto(config.server_url)

    page.fill('input[name="name"]', config.user_login)
    page.fill('input[name="password"]', config.user_password)

    time.sleep(random.uniform(1, 3))

    page.click('button[type="submit"]')

    return browser, page
