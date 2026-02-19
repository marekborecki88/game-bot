import logging

from src.application.job.job import Job
from src.domain.protocols.driver_protocol import DriverProtocol

logger = logging.getLogger(__name__)

class HeroAdventureJob(Job):

    def execute(self, ctx: AdventureContext) -> None:
        state = NavigatingState()
        while state is not None:
            state = state.execute(ctx)

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

            # Watch video to unlock additional adventure difficulty levels
            self.try_watch_video(driver)

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

            # Watch video to unlock additional adventure difficulty levels
            self.try_watch_video(driver)

            driver.click("a#closeContentButton")
            return True
        except Exception as e:
            logger.error(f"Failed to start hero adventure {e}", exc_info=True)
            return False

    def try_watch_video(self, driver: DriverProtocol) -> None:
        try:
            logger.debug("Try to watch video for hero adventure")
            # watch_video_button = "button.textButtonV2.buttonFramed.withTextAndIcon.rectangle.withText.purple:not(.buttonDisabled)"
            watch_video_button = ".bonusStatus.watchReady"
            # Should watch both video for shortening adventure time and unlocking additional difficulty levels
            video_counter = 0
            while driver.is_visible(watch_video_button):
                logger.debug("watching video for hero adventure")
                driver.click(watch_video_button)
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
                logger.debug(f"video {video_counter} for hero adventure watched")

        except Exception as e:
            logger.warning(f"Failed to watch video for hero adventure: {e}", exc_info=True)
