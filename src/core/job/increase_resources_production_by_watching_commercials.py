import logging
from dataclasses import dataclass

from src.core.job import Job
from src.core.protocols.driver_protocol import DriverProtocol


logger = logging.getLogger(__name__)

@dataclass(kw_only=True)
class IncreaseResourcesProductionByWatchingCommercialsJob(Job):

    def execute(self, driver: DriverProtocol) -> bool:
        """Watch commercials to increase resources production for 1 hour.

        Returns True if the commercial was successfully watched, False otherwise.
        """
        try:
            driver.navigate("/dorf1.php")
            driver.wait_for_selector_and_click("button.productionBoostButton")

            driver.wait_for_load_state()

            self.watch_videos(driver)

            driver.click("a#closeContentButton")

            return True
        except Exception as e:
            logger.error(f"Failed to watch commercial for production boost: {e}", exc_info=True)
            return False

    def watch_videos(self, driver: DriverProtocol) -> None:
        try:
            # <button class="textButtonV2 buttonFramed withTextAndIcon rectangle withText purple" type="button"><div><span>Activate</span><i class="videoIcon"></i></div></button>
            watch_video_selectors = "button.textButtonV2.buttonFramed.withTextAndIcon.rectangle.withText.purple:has(i.videoIcon)"
            video_counter = 0

            while driver.is_visible(watch_video_selectors):
                logger.debug("Watching commercial to boost production...")
                driver.click(watch_video_selectors)
                driver.wait_for_load_state()

                # Click confirmation dialog button
                confirmation_button = "button.textButtonV2.buttonFramed.dialogButtonOk.rectangle.withText.green"
                driver.click(confirmation_button)
                driver.wait_for_load_state()

                # Wait for video player to load
                driver.sleep(3)
                driver.wait_for_selector_and_click("#videoArea")

                # Wait for advertisement to finish
                while driver.is_visible("#videoArea"):
                    driver.sleep(5)

                video_counter += 1
                logger.debug(f"Commercial {video_counter} watched for production boost")
        except Exception as e:
            logger.error(f"Failed to watch commercial for production boost: {e}", exc_info=True)
