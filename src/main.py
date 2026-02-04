# Import only what's necessary for startup
import os
from src.config.config import Config
from src.config.logging_config import configure_logging


def setup_env() -> Config:
    """Load configuration and configure logging.

    Uses Config.load() factory which handles discovery and environment substitution.
    """
    # Load configuration (Config.load handles CONFIG_PATH discovery)
    config = Config.load()
    configure_logging(os.getenv("LOG_LEVEL", config.log_level))
    return config


def main() -> None:
    # 1. Load loggers before heavy modules are imported
    config = setup_env()

    # 2. Local imports (lazy loading)
    from playwright.sync_api import sync_playwright
    from src.core.bot import Bot
    from src.driver_adapter.driver import Driver
    from src.scan_adapter.scanner_adapter import Scanner

    with sync_playwright() as playwright:
        # Use a context manager or try/finally for the driver
        driver = Driver(playwright=playwright, driver_config=config.driver_config)
        speed = config.logic_config.speed
        try:
            bot = Bot(driver=driver, scanner=Scanner(speed), logic_config=config.logic_config)
            bot.run()
        finally:
            # Ensure the browser is closed even on error
            driver.stop()


if __name__ == "__main__":
    main()