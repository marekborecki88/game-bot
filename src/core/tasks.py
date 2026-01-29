from dataclasses import dataclass
from typing import Any

from src.core.model.model import Village
from src.core.task import Task
from src.core.driver import DriverProtocol


@dataclass(frozen=True)
class BuildTask(Task):
    village_name: str
    village_id: int
    building_id: int
    building_gid: int
    target_name: str
    target_level: int


@dataclass(frozen=True)
class BuildNewTask(Task):
    village_name: str
    village_id: int
    building_id: int
    building_gid: int
    target_name: str


@dataclass(frozen=True)
class HeroAdventureTask(Task):
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

            if driver.click_first(continue_selectors):
                return True

            # If no explicit continue button clicked, consider arrival at adventures page as success
            try:
                if "/hero/adventures" in driver.current_url():
                    return True
            except Exception:
                pass

            # Default to success because explore was clicked
            return True
        except Exception:
            # Swallow any driver exceptions and report failure
            return False


@dataclass(frozen=True)
class AllocateAttributesTask(Task):
    points: int


@dataclass(frozen=True)
class CollectDailyQuestsTask(Task):
    pass


@dataclass(frozen=True)
class CollectQuestmasterTask(Task):
    village: Village

