import sys
import time

from src.core.model.Village import Village, SourceType
from src.driver_adapter.driver import Driver
from src.scan_adapter.scanner import Scanner


def shortest_building_queue(villages: list[Village]) -> int:
    return min([v.building_queue_duration() for v in villages])

# this class should be just an interface
# the implementation should be in driver_adapter
class Bot:
    def __init__(self, driver: Driver, scanner: Scanner):
        self.driver = driver
        self.scanner = scanner

    def run(self):
        print("running bot...")
        should_exit = False
        all_villages_have_building_queue = False
        while not should_exit:
            account = self.scanner.scan()

            villages = account.villages

            print("checking villages without building queue...")

            villages_without_building_queue = [v for v in villages if v.building_queue_is_empty()]

            [self.even_build_economy(v) for v in villages_without_building_queue]

            if len(villages_without_building_queue) == 0:
                if not all_villages_have_building_queue:
                    print("All villages have building queues. Waiting...")
                all_villages_have_building_queue = True

            if all_villages_have_building_queue:
                shortest_queue_duration = shortest_building_queue(villages)

                # TODO: this value should come from config
                if shortest_queue_duration > 60 * 60 * 3:
                    print(
                        "All villages have building queues, but the shortest queue is longer than 3 hours. Exit loop.")
                    should_exit = True
                else:
                    self.wait_for_next_task(shortest_queue_duration)

    def even_build_economy(self, village: Village) -> None:
        # here we should check if first granary or warehouse upgrade is needed

        lowest_source = village.lowest_source()
        pit = village.pit_with_lowest_level_building(lowest_source)

        self.build(
            village_name=village.name,
            id=pit.id,
            gid=pit.type.value
        )

    def _refresh(self) -> None:
        self.driver.page.reload()

    def build(self, village_name: str, id: int, gid: int) -> None:
        print("building in village:", village_name, "id:", id, "pit type:",
              next((st for st in SourceType if st.value == gid), None).name)

        # I don't like this code
        self.driver.page.goto(f"{self.driver.config.server_url}/build.php?id={id}&gid={gid}")
        self.driver.page.wait_for_selector("#contract ")

        # Contract should be check by scanner and building should be queued only if enough resources

        upgrade_button = self.driver.page.locator("button.textButtonV1.green.build").first
        upgrade_button.click()
        print("Clicked upgrade button")

    def wait_for_next_task(self, seconds: int) -> None:
        print(f"Wait {seconds} seconds for next task...")
        self._count_down(seconds)

    def _count_down(self, seconds: int) -> int:
        if seconds == 0:
            sys.stdout.write('\rWaiting for next task: Finished')
            sys.stdout.flush()
            return 0
        elif seconds%60 == 0:
            self._refresh()

        sys.stdout.write(f'\rWaiting for next task: {seconds} seconds remaining')
        time.sleep(1)
        sys.stdout.flush()
        return self._count_down(seconds - 1)