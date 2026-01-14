import logging
import os
from playwright.sync_api import sync_playwright
from pathlib import Path
from src.config import load_config, Config
from src.core.bot import Bot
from src.driver_adapter.driver import Driver

config_path = Path(__file__).parent.parent / "config.yaml"
config: Config = load_config(str(config_path))

# Configure logging from config.yaml (log_level) or LOG_LEVEL env var
log_level_name = os.getenv('LOG_LEVEL', config.log_level).upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s %(levelname)-8s %(name)s - %(message)s',
)

def main():
    with sync_playwright() as playwright:
        driver: Driver = Driver(playwright=playwright, config=config)

        bot = Bot(driver=driver)
        bot.run()

        driver.stop()

if __name__ == "__main__":
    main()
