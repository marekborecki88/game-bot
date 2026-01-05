from playwright.sync_api import sync_playwright
from pathlib import Path
from app.config import load_config, Config
from app.core.bot import Bot
from app.driver_adapter.driver import Driver
from app.scan_adapter.scanner import Scanner

config_path = Path(__file__).parent.parent / "config.yaml"
config: Config = load_config(str(config_path))

def run_bot():
    print("run_bot() called")
    with sync_playwright() as playwright:
        driver: Driver = Driver(playwright=playwright, config=config)
        page = driver.login()

        scanner: Scanner = Scanner(page=page, config=config)

        bot = Bot(driver=driver, scanner=scanner)
        bot.run()

        driver.stop()


def main():
    print("main called")
    run_bot()

if __name__ == "__main__":
    main()


