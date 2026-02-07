from dataclasses import dataclass

from src.core.job.job import Job
from src.core.protocols.driver_protocol import DriverProtocol


@dataclass(kw_only=True)
class FoundNewVillageJob(Job):
    village_id: int
    village_name: str

    def execute(self, driver: DriverProtocol) -> bool:
        """Navigate to rally point and send settlers to found a new village.

        Returns True if the flow ran successfully, False otherwise.
        """
        try:
            # Navigate to the village
            driver.navigate_to_village(village_id=self.village_id)

            # Click map <a class="map" href="/karte.php" accesskey="3"></a>
            driver.click("a.map")

            x, y = self.findAbandonedValley(driver)

            # Navigate to the coordinates
            driver.navigate(f"/karte.php?x={x}&y={y}")

            # Click button Found new village
            driver.click("a:has-text('Found new village')")

            # select Gallician culture <select name="vid" id="selectTribe"><option value="">Please select tribe</option><option value="1">Romans</option><option value="2">Teutons</option><option value="3">Gauls</option><option value="6">Egyptians</option><option value="7">Huns</option><option value="8">Spartans</option></select>
            # driver.click("#selectTribe")
            # option = 3
            #
            # # select the 3rd option (Gauls)
            # for _ in range(option):
            #     driver.press_key("ArrowDown")

            driver.select_option("select#selectTribe", "3")

            driver.press_key("Enter")

            # sumbit <button type="submit" value="b40aba" name="checksum" id="checksum" class="textButtonV1 green " version="textButtonV1">Settle</button>
            driver.click("button#checksum")


            # Wait for the page to load
            driver.wait_for_load_state(timeout=3000)

            return True
        except Exception:
            return False

    def findAbandonedValley(self, driver) -> tuple[int, int]:
        return -16, -136

