"""Adapter implementing ScannerProtocol by delegating to legacy module-level functions.

This adapter provides a thin compatibility layer so callers depending on
`ScannerProtocol` can be injected with this implementation which uses the
existing `src.scan_adapter.scanner` functions.
"""
from __future__ import annotations

import json
import re

from bs4 import Tag, BeautifulSoup

from src.core.bot import CLASS_TO_RESOURCE_MAP
from src.core.model.model import (
    VillageIdentity,
    Village,
    HeroInfo,
    Account,
    SourcePit,
    Building,
    BuildingJob,
    BuildingContract,
    Resources,
    Tribe, BuildingType, ResourceType, BuildingQueue,
)
from src.core.protocols.scanner_protocol import ScannerProtocol

HTML_PARSER = 'html.parser'

class Scanner(ScannerProtocol):
    """Scanner adapter delegating to legacy scanner module functions.

    This class exposes the scanning operations as instance methods so a
    ScannerProtocol-typed object can be injected where needed.
    """

    def __init__(self, server_speed: int) -> None:
        self.speed = server_speed


    def _parse_number_value(self, text: str) -> int:
        cleaned = "".join(c for c in text if c.isdigit())
        return int(cleaned) if cleaned else 0


    def _extract_by_regex(self, pattern: str, text: str) -> str:
        """Extract the first capturing group from text using regex pattern. Raises ValueError if not found."""
        match = re.search(pattern, text)
        if not match or not match.groups():
            raise ValueError(f"Pattern {pattern} not found or no capturing group in text: '{text}'")
        return match.group(1)


    def _scan_building(self, slot: Tag) -> Building | None:
        class_attr = slot.get('class', "")
        class_str = " ".join(class_attr) if isinstance(class_attr, list) else class_attr

        # Extract gid (building type)
        gid = int(self._extract_by_regex(r'g(\d+)', class_str))

        # Skip empty slots (gid 0)
        if gid == 0:
            return None

        # Extract building slot id
        building_id = int(self._extract_by_regex(r'a(\d+)', class_str))

        # Extract level from the level element
        level_elem = slot.select_one(".labelLayer")
        level = int(level_elem.text) if level_elem else 0

        return Building(
            id=building_id,
            type=BuildingType.from_gid(gid),
            level=level,
        )


    def _parse_number(self, text: str) -> int:
        text = text.strip().replace('−', '-')
        cleaned_text = "".join(c for c in text if c.isdigit() or c == '-')
        if not cleaned_text:
            raise ValueError(f"text {text} contains no valid number")
        return int(cleaned_text)


    def _extract_number(self, entry, css_class: str) -> int:
        """Extract and parse a number value from HTML element."""
        element = entry.select_one(css_class)
        if not element:
            raise ValueError(f"Element missing {css_class}")

        return self._parse_number(element.get_text())


    def _extract_text(self, entry, css_class: str) -> str:
        """Extract text content from HTML element."""
        elem = entry.select_one(css_class)
        if not elem:
            raise ValueError(f"Element missing {css_class}")
        return elem.get_text().strip()


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

    def scan_village_list(self, html: str) -> list[VillageIdentity]:
        """Parse village names and coordinates from HTML string."""
        soup = BeautifulSoup(html, HTML_PARSER)
        village_entries = soup.select('.villageList .listEntry.village')
        return [self._parse_village_entry(entry) for entry in village_entries]

    def scan_village_name(self, dorf1: str) -> str:
        soup = BeautifulSoup(dorf1, HTML_PARSER)
        active_village = soup.select_one('.villageList .listEntry.village.active .name')
        if not active_village:
            raise ValueError("Active village name not found in HTML")
        return active_village.get_text().strip()

    def scan_account_info(self, html: str) -> Account:
        soup = BeautifulSoup(html, HTML_PARSER)
        beginners_expires = 0

        infobox = soup.select_one("#sidebarBoxInfobox")
        if infobox:

            for li in infobox.select("ul li"):
                text = li.get_text()
                timer = li.select_one(".timer")
                if timer:
                    timer_value = int(timer.get("value", "0"))

                    if "beginner's protection" in text:
                        beginners_expires = timer_value

        return Account(
            when_beginners_protection_expires=beginners_expires
        )

    def scan_village(self, identity: VillageIdentity, dorf1: str, dorf2: str) -> Village:
        # Collect stock and production data then assemble Village with Resources model
        stock = self.scan_stock_bar(dorf1)
        production = self.scan_production(dorf1)

        resources = Resources(
            lumber=stock.get("lumber", 0),
            clay=stock.get("clay", 0),
            iron=stock.get("iron", 0),
            crop=stock.get("crop", 0),
        )

        tribe = self.identity_tribe(dorf2)
        paralell_building_allowed = tribe in {Tribe.ROMANS, Tribe.HUNS}
        return Village(
            id=identity.id,
            name=self.scan_village_name(dorf1),
            tribe=tribe,
            resources=resources,
            free_crop=stock.get("free_crop", 0),
            source_pits=self.scan_village_source(dorf1),
            buildings=self.scan_village_center(dorf2),
            building_queue=self.scan_building_queue(dorf1, paralell_building_allowed),
            warehouse_capacity=stock.get("warehouse_capacity", 0),
            granary_capacity=stock.get("granary_capacity", 0),
            lumber_hourly_production=production.get("lumber_hourly_production", 0),
            clay_hourly_production=production.get("clay_hourly_production", 0),
            iron_hourly_production=production.get("iron_hourly_production", 0),
            crop_hourly_production=production.get("crop_hourly_production", 0),
            free_crop_hourly_production=production.get("free_crop_hourly_production", 0),
        )

    def is_reward_available(self, html: str) -> bool:
        """Check whether the quest/questmaster has a claimable reward visible on the page.
        We consider the quest master reward available if there is a button with id
        'questmasterButton' and it contains a class 'claimable' or a child element
        with class 'newQuestSpeechBubble' (or 'bigSpeechBubble newQuestSpeechBubble').
        """
        soup = BeautifulSoup(html, HTML_PARSER)

        # First, look for the questmaster button by ID
        btn = soup.select_one('#questmasterButton')
        if not btn:
            return False

        class_attr = btn.get('class', [])
        # normalize class list to string check
        if isinstance(class_attr, list):
            classes = ' '.join(class_attr)
        else:
            classes = str(class_attr)

        # If the button explicitly has 'claimable' class, it's available
        if 'claimable' in classes.split():
            return True

        # Alternatively, presence of a visible new quest speech bubble indicates availability
        bubble = btn.select_one('.newQuestSpeechBubble') or btn.select_one('.bigSpeechBubble.newQuestSpeechBubble')
        if bubble is not None:
            return True

        return False

    def scan_hero_info(self, hero_html: str, inventory_html: str) -> HeroInfo:
        soup = BeautifulSoup(hero_html, HTML_PARSER)
        value_elements = (self._get_item_or_raise_error(soup, ".stats", "Hero stats container not found")
                          .select(".value"))
        if len(value_elements) < 2:
            raise ValueError("Not enough stats values found for hero info")

        health = self._parse_number_value(self.clean_inner_text(value_elements[0]).replace('%', ''))
        experience = self._parse_number_value(self.clean_inner_text(value_elements[1]))
        adventure_button = self._get_item_or_raise_error(soup, "a.adventure", "Adventure button not found")
        adventures = self._parse_adventure_number(adventure_button)
        is_available = self._is_hero_available(hero_html)
        inventory = self._parse_hero_inventory(inventory_html)
        points_available = self._parse_available_attribute_points(soup)

        # detect daily quest indicator from the header/navigation if present
        nav_tag = soup.select_one('#navigation')
        daily_indicator = self.is_daily_quest_indicator(nav_tag) if nav_tag else False

        return HeroInfo(
            health=health,
            experience=experience,
            adventures=adventures,
            is_available=is_available,
            points_available=points_available,
            inventory=inventory,
            has_daily_quest_indicator=daily_indicator
        )

    # Additional helpers that tests rely on — delegate to legacy implementations
    def scan_stock_bar(self, html: str) -> dict:
        soup = BeautifulSoup(html, HTML_PARSER)
        stock_bar = soup.select_one("#stockBar")
        if not stock_bar:
            raise ValueError("Stock bar not found in HTML")

        # Parse warehouse capacity
        warehouse_capacity = self._parse_number_value(
            stock_bar.select_one(".warehouse .capacity .value").get_text()
        )

        # Parse granary capacity
        granary_capacity = self._parse_number_value(
            stock_bar.select_one(".granary .capacity .value").get_text()
        )

        # Parse resources
        lumber = self._parse_number_value(stock_bar.select_one("#l1").get_text())
        clay = self._parse_number_value(stock_bar.select_one("#l2").get_text())
        iron = self._parse_number_value(stock_bar.select_one("#l3").get_text())
        crop = self._parse_number_value(stock_bar.select_one("#l4").get_text())
        free_crop = self._parse_number_value(stock_bar.select_one("#stockBarFreeCrop").get_text())

        return {
            "lumber": lumber,
            "clay": clay,
            "iron": iron,
            "crop": crop,
            "free_crop": free_crop,
            "warehouse_capacity": warehouse_capacity,
            "granary_capacity": granary_capacity,
        }

    def scan_production(self, html: str) -> dict:
        match = re.search(r'production:\s*({[^}]*})', html)
        if not match:
            return {}

        prod_data = json.loads(match.group(1))
        return {
            "lumber_hourly_production": prod_data.get("l1", 0),
            "clay_hourly_production": prod_data.get("l2", 0),
            "iron_hourly_production": prod_data.get("l3", 0),
            "crop_hourly_production": prod_data.get("l4", 0),
            "free_crop_hourly_production": prod_data.get("l5", 0),
        }

    def scan_building_queue(self, html: str, parallel_building_allowed: bool) -> BuildingQueue:
        """Scan the building queue from the current page."""
        soup = BeautifulSoup(html, HTML_PARSER)
        queue_container = soup.select_one(".buildingList")

        building_queue = BuildingQueue(parallel_building_allowed)

        if not queue_container:
            return building_queue

        queue_items = queue_container.select("ul li")

        for item in queue_items:
            job = self._extract_building_job(item)
            building_queue.add_job(job)

        return building_queue

    def scan_village_source(self, html: str) -> list[SourcePit]:
        soup = BeautifulSoup(html, HTML_PARSER)
        container = soup.select_one("#resourceFieldContainer")
        if not container:
            raise ValueError("Resource field container not found in HTML")

        resource_fields = container.select("a")
        source_pits = []

        for field in resource_fields:
            class_attr = field.get('class', "")
            class_str = ' '.join(class_attr) if isinstance(class_attr, list) else class_attr

            # Skip if it's the village center
            if "villageCenter" in class_str:
                continue

            gid = int(self._extract_by_regex(r'gid(\d+)', class_str))

            # Map gid to SourceType
            source_type = next((st for st in ResourceType if st.gid == gid), None)

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
        soup = BeautifulSoup(html, HTML_PARSER)
        container = soup.select_one("#villageContent")
        if not container:
            raise ValueError("Village container not found in HTML")

        building_slots = container.select("div.buildingSlot")

        return [building for slot in building_slots if (building := self._scan_building(slot))]

    def identity_tribe(self, html: str) -> Tribe:
        soup = BeautifulSoup(html, HTML_PARSER)
        building_slot = soup.select_one(".buildingSlot")
        if not building_slot:
            raise ValueError("No building slot found in html to identify tribe")

        classes = building_slot.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()

        tribe_map = {
            "roman": Tribe.ROMANS,
            "teuton": Tribe.TEUTONS,
            "gaul": Tribe.GAULS,
            "huns": Tribe.HUNS,
            "spartan": Tribe.SPARTANS,
            "nors": Tribe.NORS,
            "egyptian": Tribe.EGYPTIANS,
        }

        for cls in classes:
            if cls in tribe_map:
                return tribe_map[cls]

        raise ValueError(f"Could not identify tribe from classes: {classes}")

    def _parse_adventure_number(self, adventure_button: Tag) -> int:
        content = adventure_button.select_one('div.content')
        if content is None:
            return 0
        return self._parse_number_value(content.get_text())

    def scan_new_building_contract(self, html: Tag | str) -> BuildingContract:
        """Scan the new building contract from the current page and return BuildingContract.

        Accepts a BeautifulSoup Tag or raw HTML string. Expects the contract to contain
        an element with class `resourceWrapper` containing five `.value` spans in order:
        lumber, clay, iron, crop, cropConsumption.
        """
        # Accept either Tag or raw HTML
        if isinstance(html, Tag):
            soup = html
        else:
            soup = BeautifulSoup(html or "", HTML_PARSER)

        # Resource wrapper may be nested under several containers; search broadly
        resource_wrapper = soup.select_one('.inlineIconList.resourceWrapper') or soup.select_one('.resourceWrapper')
        if not resource_wrapper:
            # fallback: if provided element is a container like #contract_building10, search within it
            resource_wrapper = soup.select_one('#contract .inlineIconList.resourceWrapper') or soup.select_one(
                '#contract .resourceWrapper')

        if not resource_wrapper:
            raise ValueError("Resource wrapper not found in building contract HTML")

        # Find all resource value elements (expected: 5 values: r1..r4 and cropConsumption)
        value_elements = resource_wrapper.select('.inlineIcon.resource .value')
        if not value_elements or len(value_elements) < 5:
            # Sometimes the last value (crop consumption) is represented with different classes
            value_elements = resource_wrapper.select('.value')

        if not value_elements or len(value_elements) < 5:
            raise ValueError("Not enough resource value elements found in contract")

        lumber = self._parse_number_value(value_elements[0].get_text())
        clay = self._parse_number_value(value_elements[1].get_text())
        iron = self._parse_number_value(value_elements[2].get_text())
        crop = self._parse_number_value(value_elements[3].get_text())
        crop_consumption = self._parse_number_value(value_elements[4].get_text())

        return BuildingContract(
            Resources(lumber=lumber,
                      clay=clay,
                      iron=iron,
                      crop=crop),
            crop_consumption=crop_consumption
        )

    def clean_inner_text(self, element) -> str:
        """Extract and clean text content from HTML element."""
        return element.get_text().strip()

    def _get_item_or_raise_error(self, item: Tag, selector: str, error_message: str = None) -> Tag:
        name_element: Tag | None = item.select_one(selector)
        if not name_element:
            raise ValueError(error_message or f"Element not found for selector: {selector} in item: {item}")
        return name_element

    def _extract_target_level(self, item):
        name_element = self._get_item_or_raise_error(item, ".name")
        name_text = name_element.get_text(separator=" ", strip=True)
        level_match = re.search(r'Level\s+(\d+)', name_text)
        return int(level_match.group(1)) if level_match else 0

    def _extract_remaining_time(self, item):
        timer_elem = item.select_one(".timer")
        time_remaining = 0
        if timer_elem:
            timer_value = timer_elem.get('value')
            if timer_value and timer_value.isdigit():
                time_remaining = int(timer_value)
        return time_remaining

    def _extract_building_job(self, item):
        target_level = self._extract_target_level(item)
        time_remaining = self._extract_remaining_time(item)
        building_name = self._extract_building_name_from_builing_job(item)

        return BuildingJob(
            building_name = building_name,
            target_level=target_level,
            time_remaining=time_remaining,
        )

    def _is_hero_available(self, html: str) -> bool:
        """Check if hero is available for adventures."""
        soup = BeautifulSoup(html, HTML_PARSER)
        hero_state = soup.select_one(".heroState")

        if not hero_state:
            # If no heroState element found, assume hero is available
            return True

        state_text = self.clean_inner_text(hero_state)

        # Hero is available only if they are "currently in village"
        # Any other status (on the way, traveling, etc) means unavailable
        return "currently in village" in state_text

    def _parse_hero_inventory(self, inventory_html: str) -> dict:
        """Parse hero inventory (resources) from inventory HTML. Returns a dict or empty dict if not found."""
        if not inventory_html:
            return {}

        soup = BeautifulSoup(inventory_html, HTML_PARSER)
        items = soup.find_all("div", class_="heroItem")

        inventory = {}
        for i in items:
            classes = i.find("div", class_="item").get("class")
            if len(classes) == 3:
                key = CLASS_TO_RESOURCE_MAP.get(classes[1])
                if key:
                    text_value = i.find("div", class_="count").get_text()
                    inventory[key] = int(text_value)

        return inventory

    def _parse_available_attribute_points(self, soup: BeautifulSoup) -> int:
        points_elem = soup.select_one(".pointsAvailable")
        if not points_elem:
            return 0
        return self._parse_number_value(points_elem.get_text())

    def _class_list_to_str(self, class_attr) -> str:
        """Normalize class attribute (string or list) to space-joined string."""
        if isinstance(class_attr, list):
            return ' '.join(class_attr)
        return str(class_attr or '')

    # TODO: add configuration option to enable/disable this scan and to set threshold values for minumum reward points
    def is_daily_quest_indicator(self, nav_tag: Tag) -> bool:
        """Return True if provided Tag contains <a.dailyQuests> with a child div.indicator whose text is exactly '!'.

        Expect a BeautifulSoup Tag (e.g., soup or subtag). Keep implementation minimal and explicit.
        """
        if not isinstance(nav_tag, Tag):
            return False

        anchor = nav_tag.select_one('a.dailyQuests')
        if not anchor:
            return False

        indicator = anchor.select_one('div.indicator')
        if not indicator:
            return False

        return indicator.get_text().strip() == '!'

    def _extract_building_name_from_builing_job(self, item):
        return item.select_one('.name').text.split("Level")[0].strip()

