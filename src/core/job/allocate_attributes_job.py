from dataclasses import dataclass

from src.core.job.job import Job
from src.core.protocols.driver_protocol import DriverProtocol
from src.core.model.model import DEFAULT_ATTRIBUTE_POINT_TYPE


@dataclass(kw_only=True)
class AllocateAttributesJob(Job):
    points: int

    def execute(self, driver: DriverProtocol) -> bool:
        """Allocate hero attribute points using driver primitives.

        Returns True on success, False on failure.
        """
        try:
            # Navigate and ensure hero attributes section is present
            driver.navigate('/hero/attributes')
            present = driver.wait_for_selector('div.heroAttributes', timeout=3000)
            if not present:
                return False

            buttons_selector = "button.textButtonV2.buttonFramed.plus.rectangle.withIcon.green, [role=\"button\"].textButtonV2.buttonFramed.plus.rectangle.withIcon.green"

            target_index = DEFAULT_ATTRIBUTE_POINT_TYPE.value - 1

            # Click the N-th plus button points times
            for _ in range(self.points):
                driver.click_nth(buttons_selector, target_index)

            saved = driver.click_first(['#savePoints', 'button#savePoints'])
            driver.click("a#closeContentButton")

            return saved
        except Exception:
            return False
