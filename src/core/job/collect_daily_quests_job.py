from dataclasses import dataclass

from src.core.job.job import Job
from src.core.protocols.driver_protocol import DriverProtocol

DAILY_QUESTS_SELECTOR = '#navigation a.dailyQuests'
CLOSE_WINDOW_BUTTON_SELECTOR = "a#closeContentButton"
CONFIRM_COLLECT_REWARDS_BUTTON_SELECTOR = ".textButtonV2.buttonFramed.collect.collectable.rectangle.withText.green"
COLLECT_REWARDS_BUTTON_SELECTOR = ".textButtonV2.buttonFramed.collectRewards.rectangle.withText.green"


@dataclass(kw_only=True)
class CollectDailyQuestsJob(Job):
    def execute(self, driver: DriverProtocol) -> bool:
        """Click the daily quests anchor and collect rewards using driver primitives.

        Returns True if the flow ran (click attempts made), False otherwise.
        """
        try:
            driver.wait_for_selector_and_click(DAILY_QUESTS_SELECTOR)
            driver.wait_for_selector_and_click(COLLECT_REWARDS_BUTTON_SELECTOR)
            driver.wait_for_selector_and_click(CONFIRM_COLLECT_REWARDS_BUTTON_SELECTOR)
            driver.wait_for_selector_and_click(CLOSE_WINDOW_BUTTON_SELECTOR)
            return True
        except Exception:
            return False
