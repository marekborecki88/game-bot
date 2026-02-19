# Import only what's necessary for startup
import os
from src.domain.config import Config
from src.config.logging_config import configure_logging
from src.infrastructure.config_loader import load


def setup_env() -> Config:
    """Load configuration and configure logging.

    Uses Config.load() factory which handles discovery and environment substitution.
    """
    # Load configuration (Config.load handles CONFIG_PATH discovery)
    config = load()
    configure_logging(os.getenv("LOG_LEVEL", config.log_level))
    return config


def main() -> None:
    # 1. Load loggers before heavy modules are imported
    config = setup_env()

    # 2. Local imports (lazy loading)
    from playwright.sync_api import sync_playwright
    from src.domain.bot import Bot
    from src.infrastructure.driver_adapter.driver import Driver
    from src.infrastructure.scan_adapter.scanner_adapter import Scanner

    with sync_playwright() as playwright:
        # Use a context manager or try/finally for the driver
        driver = Driver(playwright=playwright, driver_config=config.driver_config)
        speed = config.logic_config.speed
        try:
            bot = Bot(driver=driver, scanner=Scanner(speed), logic_config=config.logic_config, hero_config=config.hero_config)
            bot.run()
        except KeyboardInterrupt:
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Keyboard interrupt received, shutting down...")
        finally:
            # Ensure the browser is closed even on error
            driver.stop()


if __name__ == "__main__":
    main()