import re

from bs4 import BeautifulSoup
from playwright.sync_api import Page, Locator

from src.config import Config
from src.core.model.Village import BuildingType, Village, SourcePit, SourceType, Building, BuildingJob, VillageIdentity


def _parse_resource_value(text: str) -> int:
    """Parse resource value from text, removing UNICODE markers and formatting."""
    cleaned = "".join(c for c in text if c.isdigit())
    return int(cleaned) if cleaned else 0


def clean_inner_text(html) -> str:
    return html.inner_text().strip()


def parse_int_or_zero(text_number: Locator):
    if text_number.count() > 0:
        level_text = clean_inner_text(text_number.first)
        if level_text.isdigit():
            return int(level_text)

    return 0

#TODO: this class should be refactored
# it should just accept peaces of html and return data models
# methods of this class should be invoked by other part of the app where driver is invoked as well to grab html
class Scanner:
    def __init__(self, page: Page = None, config: Config = None):
        self.page = page
        self.config = config


    def _extract_text(self, entry, css_class: str) -> str:
        """Extract text content from HTML element."""
        elem = entry.select_one(css_class)
        if not elem:
            raise ValueError(f"Element missing {css_class}")
        return elem.get_text().strip()

    def _extract_number(self, entry, css_class: str) -> int:
        """Extract and parse a number value from HTML element."""
        element = entry.select_one(css_class)
        if not element:
            raise ValueError(f"Element missing {css_class}")

        return self._parse_number(element.get_text())

    def _parse_number(self, text: str) -> int:
        text = text.strip().replace('−', '-')
        cleaned_text = "".join(c for c in text if c.isdigit() or c == '-')
        if not cleaned_text:
            raise ValueError(f"text {text} contains no valid number")
        return int(cleaned_text)

    def _parse_village_entry(self, entry) -> VillageIdentity:
        """Parse a single village entry from HTML element."""
        village_id = entry.get('data-did')
        if not village_id:
            raise ValueError("Village entry missing data-did attribute")

        name = self._extract_text(entry, '.name')
        coordinate_x = self._extract_number(entry, '.coordinateX')
        coordinate_y = self._extract_number(entry, '.coordinateY')

        return VillageIdentity(
            id=int(village_id),
            name=name,
            coordinate_x=coordinate_x,
            coordinate_y=coordinate_y
        )

    def _extract_by_regex(self, pattern: str, text: str) -> str:
        """Extract the first capturing group from text using regex pattern. Raises ValueError if not found."""
        match = re.search(pattern, text)
        if not match or not match.groups():
            raise ValueError(f"Pattern {pattern} not found or no capturing group in text: '{text}'")
        return match.group(1)

    def scan_village_list(self, html: str) -> list[VillageIdentity]:
        """Parse village names and coordinates from HTML string."""
        soup = BeautifulSoup(html, 'html.parser')
        village_entries = soup.select('.villageList .listEntry.village')
        return [self._parse_village_entry(entry) for entry in village_entries]


    def scan_village_source(self, html: str) -> list[SourcePit]:
        """Scan all resource fields from the village resource view."""
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.select_one("#resourceFieldContainer")
        if not container:
            raise ValueError("Resource field container not found in HTML")

        resource_fields = container.select("a")
        source_pits = []

        for field in resource_fields:
            class_attr = field.get('class', [])
            class_str = ' '.join(class_attr) if isinstance(class_attr, list) else class_attr

            # Skip if it's the village center
            if "villageCenter" in class_str:
                continue

            gid = int(self._extract_by_regex(r'gid(\d+)', class_str))

            # Map gid to SourceType
            source_type = next((st for st in SourceType if st.value == gid), None)

            # Extract buildingSlot (field id)
            field_id = int(self._extract_by_regex(r'buildingSlot(\d+)', class_str))

            # Extract level
            level_match = re.search(r'level(\d+)', class_str)
            level = int(level_match.group(1)) if level_match else 0

            source_pits.append(SourcePit(
                id=field_id,
                type=source_type,
                level=level,
            ))

        return source_pits

    def scan_village_center(self, html: str) -> list[Building]:
        """Scan all buildings from the village center view."""

        self.page.goto(f"{self.config.server_url}/dorf2.php")
        self.page.wait_for_selector("#villageContent")

        container = self.page.locator("#villageContent")
        building_slots = container.locator("div.buildingSlot")

        buildings = []

        for i in range(building_slots.count()):
            slot = building_slots.nth(i)
            class_attr = slot.get_attribute("class") or ""

            # Extract gid (building type)
            gid = int(self._extract_by_regex(r'g(\d+)', class_attr))

            # Skip empty slots (gid 0)
            if gid == 0:
                continue

            # Map gid to BuildingType
            building_type = next((bt for bt in BuildingType if bt.value == gid), None)

            # Extract building slot id
            building_id = int(self._extract_by_regex(r'a(\d+)', class_attr))

            # Extract level from the level element
            level_elem = slot.locator(".labelLayer")
            level = parse_int_or_zero(level_elem.first)

            buildings.append(Building(
                id=building_id,
                type=building_type,
                level=level,
            ))

        return buildings


    def scan_building_queue(self, html: str) -> list[BuildingJob]:
        """Scan the building queue from the current page."""
        building_queue = []

        # Building queue is in .buildingList
        queue_container = self.page.locator(".buildingList")
        if queue_container.count() == 0:
            return building_queue

        queue_items = queue_container.locator("li")

        for i in range(queue_items.count()):
            item = queue_items.nth(i)

            # Extract building name and level from the text
            name_elem = item.locator(".name")
            if name_elem.count() == 0:
                continue

            level_match = re.search(r'(\d+)$', clean_inner_text(name_elem))
            target_level = int(level_match.group(1)) if level_match else 0

            # Extract building id from the link or data attribute
            link = item.locator("a").first
            href = link.get_attribute("href") or ""
            id_match = re.search(r'id=(\d+)', href)
            building_id = int(id_match.group(1)) if id_match else 0

            # Extract remaining time in seconds
            timer_elem = item.locator(".timer")
            time_remaining = 0
            if timer_elem.count() > 0:
                timer_value = timer_elem.get_attribute("value")
                if timer_value and timer_value.isdigit():
                    time_remaining = int(timer_value)

            building_queue.append(BuildingJob(
                building_id=building_id,
                target_level=target_level,
                time_remaining=time_remaining,
            ))

        return building_queue


    def scan_stock_bar(self, html: str) -> dict:
        stock_bar = self.page.locator("#stockBar")

        # Parse warehouse capacity
        warehouse_capacity = _parse_resource_value(
            stock_bar.locator(".warehouse .capacity .value").inner_text()
        )

        # Parse granary capacity
        granary_capacity = _parse_resource_value(
            stock_bar.locator(".granary .capacity .value").inner_text()
        )

        # Parse resources
        lumber = _parse_resource_value(stock_bar.locator("#l1").inner_text())
        clay = _parse_resource_value(stock_bar.locator("#l2").inner_text())
        iron = _parse_resource_value(stock_bar.locator("#l3").inner_text())
        crop = _parse_resource_value(stock_bar.locator("#l4").inner_text())
        free_crop = _parse_resource_value(stock_bar.locator("#stockBarFreeCrop").inner_text())

        return {
            "lumber": lumber,
            "clay": clay,
            "iron": iron,
            "crop": crop,
            "free_crop": free_crop,
            "warehouse_capacity": warehouse_capacity,
            "granary_capacity": granary_capacity,
        }

    def scan_village(self, village_id: int, dorf1, dorf2) -> Village:
        return Village(
            id=village_id,
            name=(self.scan_village_name(dorf1)),
            source_pits=(self.scan_village_source(dorf1)),
            buildings=(self.scan_village_center(dorf2)),
            building_queue=(self.scan_building_queue(dorf1)),
            **(self.scan_stock_bar(dorf1))
        )


    def scan(self, dorf1: str) -> list[Village]:
        print("scanning account...")

        village_identities = self.scan_village_list(dorf1)
        return [self.scan_village(village.id, dorf1, dorf1) for village in village_identities]

    def scan_village_name(self, dorf1) -> str:
        pass

