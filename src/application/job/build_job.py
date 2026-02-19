from dataclasses import dataclass
from datetime import datetime
import logging

from src.domain.model.model import Resources
from src.application.job.job import Job
from src.domain.protocols.driver_protocol import DriverProtocol
from src.infrastructure.scan_adapter.scanner_adapter import Scanner

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class BuildJob(Job):
    village_name: str
    village_id: int
    building_id: int
    building_gid: int
    target_name: str
    target_level: int
    support: Resources | None = None
    freeze_until: datetime | None = None
    freeze_queue_key: str | None = None

    def execute(self, driver: DriverProtocol) -> bool:
        """Perform building/upgrade action using driver primitives.

        Returns True if the primary action (clicking the build/upgrade button)
        was attempted, False otherwise.
        """
        # Navigate directly to the build URL for the given slot and gid
        driver.navigate(f"/build.php?newdid={self.village_id}&id={self.building_id}&gid={self.building_gid}")

        if self.support:
            # Fill in support resources if provided
            driver.transfer_resources_from_hero(self.support)
            # after transfer go back to the contract site
            driver.navigate(f"/build.php?newdid={self.village_id}&id={self.building_id}&gid={self.building_gid}")

        # Wait for contract UI to appear
        if not driver.wait_for_selector('#contract', timeout=3000):
            return False

        # # Try common upgrade button selector
        normal_duration_selector = ".section1 .value"
        faster_duration_selector = ".section2 .value"
        normal_duration_text = driver.get_text_content(normal_duration_selector)
        faster_duration_text = driver.get_text_content(faster_duration_selector)

        normal_duration = self._parse_duration(normal_duration_text)
        faster_duration = self._parse_duration(faster_duration_text)

        duration_difference = normal_duration - faster_duration

        if duration_difference > 0:  # 2 minutes in seconds
            success = self.watch_video(driver, duration_difference)
            if not success:
                logger.debug("Failed to watch video or video time is not sufficient, proceeding with normal build")
                return driver.click("button.textButtonV1.green.build")
        else:
            return driver.click("button.textButtonV1.green.build")


    def _parse_duration(self, duration_text: str) -> int:
        """Parse duration string in format HH:MM:SS to total seconds."""
        parts = duration_text.strip().split(":")
        if len(parts) != 3:
            print(f"Unexpected duration format: '{duration_text}', patts: {parts}")
            raise ValueError(f"Invalid duration format: {duration_text}")
        hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        return hours * 3600 + minutes * 60 + seconds

        #.section1 .value
        # Try alternative selector for upgrade button

    def watch_video(self, driver: DriverProtocol, duration_difference: int) -> bool:
        try:
            logger.debug("Try to watch video for shortening build time")
            # watch_video_button = "button.textButtonV2.buttonFramed.withTextAndIcon.rectangle.withText.purple:not(.buttonDisabled)"
            watch_video_button = "button.textButtonV1.purple.build.videoFeatureButton"
            # Should watch both video for shortening adventure time and unlocking additional difficulty levels
            video_counter = 0
            while driver.is_visible(watch_video_button):
                driver.wait_for_selector_and_click(watch_video_button)
                logger.debug("watching video for hero adventure")

                # Click confirmation dialog button
                driver.wait_for_selector_and_click("button.textButtonV2.buttonFramed.dialogButtonOk.rectangle.withText.green")

                # Wait for video player to load
                driver.sleep(2)
                driver.wait_for_selector_and_click("#videoArea")

                remaining_time = self.read_remaining_time(driver)

                # Wait for advertisement to finish
                while driver.is_visible("#videoArea"):
                    remaining_time = self.read_remaining_time(driver)

                    if remaining_time > duration_difference:
                        logger.debug(f"Remaining video time {remaining_time} is longer than duration difference {duration_difference}")
                        self.stop_video(driver)
                        return False

                    driver.sleep(5)

                video_counter += 1
                logger.debug(f"video {video_counter} for hero adventure watched")

        except Exception as e:
            logger.warning(f"Failed to watch video for hero adventure: {e}", exc_info=True)
            return False

        return True

    def read_remaining_time(self, driver: DriverProtocol) -> int:
        """Read remaining time from video advertisement counter.

        Returns 0 if the counter is not visible or not yet initialized.
        """
        html = driver.get_page_source(iframe_selector="#videoArea")

        # Check if the remaining time wrapper is hidden
        if "atg-gima-remaining-time-wrapper atg-gima-hidden" in html:
            logger.debug("Video counter is hidden, video may not have started yet")
            return 0

        scanner = Scanner(server_speed=5)
        remaining_time = scanner.scan_advertise_remaining_time(html)

        if remaining_time == 0:
            logger.debug("Video counter is empty or not initialized yet")

        return remaining_time


    def stop_video(self, driver: DriverProtocol) -> None:
        logger.debug("Stopping video playback")
        # This selector is based on the structure of the video player and may need to be updated if the player changes
        stop_button_selector = "div.dialogCancelButton.iconButton.buttonFramed.green.withIcon.rectangle.cancel"
        if driver.is_visible(stop_button_selector):
            driver.wait_for_selector_and_click(stop_button_selector)
            driver.wait_for_selector_and_click("button.textButtonV2.buttonFramed.rectangle.withText.green")
            logger.debug("Video playback stopped successfully")
        else:
            logger.warning("Stop button not found, unable to stop video playback")