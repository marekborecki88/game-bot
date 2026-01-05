from playwright.sync_api import sync_playwright

from app.config import load_config, Config
from app.core.bot import Bot
from app.driver_adapter.driver import Driver
from app.scan_adapter.scanner import Scanner

config: Config = load_config("../config.yaml")

def run_bot():
    with sync_playwright() as playwright:
        driver: Driver = Driver(playwright=playwright, config=config)
        page = driver.login()

        scanner: Scanner = Scanner(page=page, config=config)

        bot = Bot(driver=driver, scanner=scanner)
        bot.run()

        driver.stop()


run_bot()
