from app.core.model.Village import Village
from app.driver_adapter.driver import Driver
from app.scan_adapter.scanner import Scanner


class Bot:
    def __init__(self, driver: Driver, scanner: Scanner):
        self.driver = driver
        self.scanner = scanner

    def run(self):
        exit = False
        while not exit:
            villages = self.scanner.scan().villages

            [self.even_build_economy(v) for v in villages if v.building_queue_is_empty()]

            exit = True


    def even_build_economy(self, village: Village) -> None:
        # here we should check if first granary or warehouse upgrade is needed

        lowest_source = village.lowest_source()
        pit = village.pit_with_lowest_level_building(lowest_source)

        self.build(
            village_name=village.name,
            id=pit.id,
            gid=pit.type.value
        )

    def build(self, village_name: str, id: int, gid: int) -> None:
        print("building in village:", village_name, "id:", id, "gid:", gid)

        # I don't like this code
        self.driver.page.goto(f"{self.driver.config.server_url}/build.php?id={id}&gid={gid}")
        self.driver.page.wait_for_selector("#contract ")

        # Contract should be check by scanner and building should be queued only if enough resources

        upgrade_button = self.driver.page.locator("button.textButtonV1.green.build").first
        upgrade_button.click()
        print("Clicked upgrade button")