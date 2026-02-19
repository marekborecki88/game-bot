from dataclasses import dataclass

from src.application.job.job import Job
from src.domain.model.village import Village
from src.domain.protocols.driver_protocol import DriverProtocol


@dataclass(kw_only=True)
class CollectQuestmasterJob(Job):
    village: Village

    def execute(self, driver: DriverProtocol) -> bool:
        """Collect questmaster rewards if available.

        Returns True if any click attempts were made (rewards collected or attempted), False otherwise.
        """
        try:
            driver.wait_for_selector_and_click('#questmasterButton')

            # Click all 'Collect' controls
            collect_selectors = ["button:has-text('Collect')"]

            clicks = 0
            # iterate through reward pages until forward button is disabled
            while True:
                driver.wait_for_selector("button:has-text('Collect')")
                clicks += driver.click_all(collect_selectors)
                # sleep 1 second to allow page to update
                driver.sleep(1)
                classes = driver.catch_full_classes_by_selector("button.forward")
                if "disabled" not in classes:
                    driver.click("button.forward")
                    continue

                break


            # click general tasks
            driver.wait_for_selector_and_click("a.tabItem:has-text('General tasks')")
            clicks += driver.click_all(collect_selectors)

            driver.click("a#closeContentButton")
            return clicks > 0
        except Exception:
            return False
