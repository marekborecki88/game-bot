from dataclasses import dataclass

from src.core.job.job import Job
from src.core.model.model import Village
from src.core.protocols.driver_protocol import DriverProtocol


@dataclass(kw_only=True)
class FoundNewVillageJob(Job):
    village: Village

    def execute(self, driver: DriverProtocol) -> bool:
        """Navigate to rally point and send settlers to found a new village.

        Returns True if the flow ran successfully, False otherwise.
        """
        try:
            # Navigate to the village
            driver.navigate_to_village(village_id=self.village_id)

            # Click map <a class="map" href="/karte.php" accesskey="3"></a>
            driver.click("a.map")

            x, y = self.findNearestAbandonedValley(driver, self.village.coordinates)

            # Navigate to the coordinates
            driver.navigate(f"/karte.php?x={x}&y={y}")

            # Click button Found new village
            driver.click("a:has-text('Found new village')")

            #TODO: it should be configurable
            # if tribe is selectable, choose tribe 3 (Gauls)
            if driver.is_visible("select#selectTribe"):
                driver.select_option("select#selectTribe", "3")

            driver.press_key("Enter")

            # sumbit <button type="submit" value="b40aba" name="checksum" id="checksum" class="textButtonV1 green " version="textButtonV1">Settle</button>
            driver.click("button#checksum")


            # Wait for the page to load
            driver.wait_for_load_state(timeout=3000)

            return True
        except Exception:
            return False

    def findNearestAbandonedValley(self, driver: DriverProtocol, coordinates: tuple[int, int]) -> tuple[int, int]:
        driver.scan_map(coordinates)

