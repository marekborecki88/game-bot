from dataclasses import dataclass
from typing import Any

from src.core.job.job import Job
from src.core.protocols.driver_protocol import DriverProtocol


@dataclass(kw_only=True)
class HeroAdventureJob(Job):
    hero_info: Any

    def execute(self, driver: DriverProtocol) -> bool:
        """Start a hero adventure using the provided driver primitives.

        The Task is responsible for orchestration: navigating to the hero
        adventures page, clicking the Explore button, waiting for UI updates,
        attempting to click any Continue control and finally inferring
        success from the current URL if needed.
        """
        try:
            # Navigate to hero adventures view
            driver.navigate("/hero/adventures")

            # Exact selector where the green Explore button typically lives
            explore_selector = "button.textButtonV2.buttonFramed.rectangle.withText.green"
            clicked = driver.click(explore_selector)
            if not clicked:
                # Explore button not found or not visible
                return False

            # Allow UI to update
            driver.wait_for_load_state()

            # Try continue selectors
            continue_selectors = [
                "button.textButtonV2.buttonFramed.continue.rectangle.withText.green",
                "text=Continue",
                "button.continue",
                "a.continue",
                "button.button.green",
                "a.button.green",
                "button:has-text('Continue')",
                "a:has-text('Continue')",
            ]

            success = driver.click_first(continue_selectors)

            if not success:
                return False

            driver.click("a#closeContentButton")
            return True
        except Exception:
            # Swallow any driver exceptions and report failure
            return False
