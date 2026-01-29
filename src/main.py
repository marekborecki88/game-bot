from pathlib import Path
import os
from typing import Optional

# Import only what's necessary for startup
from src.config import load_config, Config
from src.core.logging_config import configure_logging

def setup_env() -> Config:
    """Configure the environment and return the configuration object."""
    # Tip: You can allow passing the path via an environment variable
    default_path = Path(__file__).parent.parent / "config.yaml"
    cfg_path = os.getenv("CONFIG_PATH", str(default_path))
    
    config = load_config(cfg_path)
    configure_logging(os.getenv("LOG_LEVEL", config.log_level))
    return config

def main() -> None:
    # 1. Load loggers before heavy modules are imported
    config = setup_env()

    # 2. Local imports (lazy loading)
    from playwright.sync_api import sync_playwright
    from src.core.bot import Bot
    from src.driver_adapter.driver import Driver

    with sync_playwright() as playwright:
        # Use a context manager or try/finally for the driver
        driver = Driver(playwright=playwright, config=config)
        try:
            bot = Bot(driver=driver)
            bot.run()
        finally:
            # Ensure the browser is closed even on error
            driver.stop()

if __name__ == "__main__":
    main()