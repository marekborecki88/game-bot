from playwright.sync_api import sync_playwright
from pathlib import Path
from src.config import load_config, Config
from src.core.bot import Bot
from src.driver_adapter.driver import Driver
from src.scan_adapter.scanner import Scanner

config_path = Path(__file__).parent.parent / "config.yaml"
config: Config = load_config(str(config_path))

def run_bot():
    with sync_playwright() as playwright:
        driver: Driver = Driver(playwright=playwright, config=config)
        page = driver.login()

        scanner: Scanner = Scanner(page=page, config=config)

        bot = Bot(driver=driver, scanner=scanner)
        bot.run()

        driver.stop()


def main():
    run_bot()

if __name__ == "__main__":
    main()


