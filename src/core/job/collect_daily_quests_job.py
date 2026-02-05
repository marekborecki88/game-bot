from dataclasses import dataclass

from src.core.job.job import Job
from src.core.protocols.driver_protocol import DriverProtocol

DAILY_QUESTS_SELECTOR = '#navigation a.dailyQuests'
CLOSE_WINDOW_BUTTON_SELECTOR = "a#closeContentButton"
CONFIRM_COLLECT_REWARDS_BUTTON_SELECTOR = ".textButtonV2.buttonFramed.collect.collectable.rectangle.withText.green"
COLLECT_REWARDS_BUTTON_SELECTOR = ".textButtonV2.buttonFramed.collectRewards.rectangle.withText.green"
ACHIEVED_POINTS_SELECTOR = ".achievedPoints .achieved"


@dataclass(kw_only=True)
class CollectDailyQuestsJob(Job):
    daily_quest_threshold: int

    def execute(self, driver: DriverProtocol) -> bool:
        """Click the daily quests anchor and collect rewards if points threshold is met.

        Returns True if the flow ran (click attempts made), False otherwise.
        """
        try:
            driver.wait_for_selector_and_click(DAILY_QUESTS_SELECTOR)

            # Wait for the dialog to appear and check achieved points
            driver.wait_for_selector(ACHIEVED_POINTS_SELECTOR, timeout=3000)
            points_text = driver.get_text_content(ACHIEVED_POINTS_SELECTOR)

            try:
                achieved_points = int(points_text.strip())
            except ValueError:
                # If we can't parse points, close dialog and return False
                driver.wait_for_selector_and_click(CLOSE_WINDOW_BUTTON_SELECTOR)
                return False

            # Check if threshold is met
            if achieved_points < self.daily_quest_threshold:
                # Points below threshold - close dialog without collecting
                driver.wait_for_selector_and_click(CLOSE_WINDOW_BUTTON_SELECTOR)
                return False

            # Threshold met - collect rewards
            driver.wait_for_selector_and_click(COLLECT_REWARDS_BUTTON_SELECTOR)
            driver.wait_for_selector_and_click(CONFIRM_COLLECT_REWARDS_BUTTON_SELECTOR)
            driver.wait_for_selector_and_click(CLOSE_WINDOW_BUTTON_SELECTOR)
            return True
        except Exception:
            return False
