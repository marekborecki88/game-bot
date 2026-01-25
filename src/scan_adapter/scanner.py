import json
import re

from bs4 import BeautifulSoup, Tag
from src.core.model.model import BuildingType, Village, SourcePit, SourceType, Building, BuildingJob, VillageIdentity, \
    Account, Tribe, HeroInfo

HTML_PARSER = 'html.parser'


def _parse_number_value(text: str) -> int:
    cleaned = "".join(c for c in text if c.isdigit())
    return int(cleaned) if cleaned else 0


def clean_inner_text(element) -> str:
    """Extract and clean text content from HTML element."""
    return element.get_text().strip()


def _extract_by_regex(pattern: str, text: str) -> str:
    """Extract the first capturing group from text using regex pattern. Raises ValueError if not found."""
    match = re.search(pattern, text)
    if not match or not match.groups():
        raise ValueError(f"Pattern {pattern} not found or no capturing group in text: '{text}'")
    return match.group(1)


def _scan_building(slot: Tag) -> Building | None:
    class_attr = slot.get('class', "")
    class_str = " ".join(class_attr) if isinstance(class_attr, list) else class_attr

    # Extract gid (building type)
    gid = int(_extract_by_regex(r'g(\d+)', class_str))

    # Skip empty slots (gid 0)
    if gid == 0:
        return None

    # Extract building slot id
    building_id = int(_extract_by_regex(r'a(\d+)', class_str))

    # Extract level from the level element
    level_elem = slot.select_one(".labelLayer")
    level = int(level_elem.text) if level_elem else 0

    return Building(
        id=building_id,
        type=BuildingType.from_gid(gid),
        level=level,
    )


def scan_village_name(dorf1: str) -> str:
    soup = BeautifulSoup(dorf1, HTML_PARSER)
    active_village = soup.select_one('.villageList .listEntry.village.active .name')
    if not active_village:
        raise ValueError("Active village name not found in HTML")
    return active_village.get_text().strip()


def scan_stock_bar(html: str) -> dict:
    soup = BeautifulSoup(html, HTML_PARSER)
    stock_bar = soup.select_one("#stockBar")
    if not stock_bar:
        raise ValueError("Stock bar not found in HTML")

    # Parse warehouse capacity
    warehouse_capacity = _parse_number_value(
        stock_bar.select_one(".warehouse .capacity .value").get_text()
    )

    # Parse granary capacity
    granary_capacity = _parse_number_value(
        stock_bar.select_one(".granary .capacity .value").get_text()
    )

    # Parse resources
    lumber = _parse_number_value(stock_bar.select_one("#l1").get_text())
    clay = _parse_number_value(stock_bar.select_one("#l2").get_text())
    iron = _parse_number_value(stock_bar.select_one("#l3").get_text())
    crop = _parse_number_value(stock_bar.select_one("#l4").get_text())
    free_crop = _parse_number_value(stock_bar.select_one("#stockBarFreeCrop").get_text())

    return {
        "lumber": lumber,
        "clay": clay,
        "iron": iron,
        "crop": crop,
        "free_crop": free_crop,
        "warehouse_capacity": warehouse_capacity,
        "granary_capacity": granary_capacity,
    }


def scan_production(html: str) -> dict:
    match = re.search(r'production:\s*({[^}]*})', html)
    if not match:
        return {}

    prod_data = json.loads(match.group(1))
    return {
        "lumber_hourly_production": prod_data.get("l1", 0),
        "clay_hourly_production": prod_data.get("l2", 0),
        "iron_hourly_production": prod_data.get("l3", 0),
        "crop_hourly_production": prod_data.get("l4", 0),
    }


def _get_item_or_raise_error(item: Tag, selector: str, error_message: str = None) -> Tag:
    name_element: Tag | None = item.select_one(selector)
    if not name_element:
        raise ValueError(error_message or f"Element not found for selector: {selector} in item: {item}")
    return name_element


def _extract_target_level(item):
    name_element = _get_item_or_raise_error(item, ".name")
    name_text = name_element.get_text(separator=" ", strip=True)
    level_match = re.search(r'Level\s+(\d+)', name_text)
    return int(level_match.group(1)) if level_match else 0


def _extract_remaining_time(item):
    timer_elem = item.select_one(".timer")
    time_remaining = 0
    if timer_elem:
        timer_value = timer_elem.get('value')
        if timer_value and timer_value.isdigit():
            time_remaining = int(timer_value)
    return time_remaining


def _extract_building_job(item):
    target_level = _extract_target_level(item)
    time_remaining = _extract_remaining_time(item)

    return BuildingJob(
        building_id=0,  # Cannot easily determine building_id from this view
        target_level=target_level,
        time_remaining=time_remaining,
    )


def scan_building_queue(html: str) -> list[BuildingJob]:
    """Scan the building queue from the current page."""
    soup = BeautifulSoup(html, HTML_PARSER)
    queue_container = soup.select_one(".buildingList")

    if not queue_container:
        return []

    queue_items = queue_container.select("ul li")
    return [_extract_building_job(item) for item in queue_items]


def _extract_text(entry, css_class: str) -> str:
    """Extract text content from HTML element."""
    elem = entry.select_one(css_class)
    if not elem:
        raise ValueError(f"Element missing {css_class}")
    return elem.get_text().strip()


def _parse_number(text: str) -> int:
    text = text.strip().replace('−', '-')
    cleaned_text = "".join(c for c in text if c.isdigit() or c == '-')
    if not cleaned_text:
        raise ValueError(f"text {text} contains no valid number")
    return int(cleaned_text)


def scan_village_source(html: str) -> list[SourcePit]:
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

        gid = int(_extract_by_regex(r'gid(\d+)', class_str))

        # Map gid to SourceType
        source_type = next((st for st in SourceType if st.gid == gid), None)

        # Extract buildingSlot (field id)
        field_id = int(_extract_by_regex(r'buildingSlot(\d+)', class_str))

        # Extract level
        level_match = re.search(r'level(\d+)', class_str)
        level = int(level_match.group(1)) if level_match else 0

        source_pits.append(SourcePit(
            id=field_id,
            type=source_type,
            level=level,
        ))

    return source_pits


def scan_village_center(html: str) -> list[Building]:
    soup = BeautifulSoup(html, HTML_PARSER)
    container = soup.select_one("#villageContent")
    if not container:
        raise ValueError("Village container not found in HTML")

    building_slots = container.select("div.buildingSlot")

    return [building for slot in building_slots if (building := _scan_building(slot))]


def identity_tribe(dorf2: str) -> Tribe:
    soup = BeautifulSoup(dorf2, HTML_PARSER)
    building_slot = soup.select_one(".buildingSlot")
    if not building_slot:
        raise ValueError("No building slot found in dorf2.html to identify tribe")

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


def scan_village(identity: VillageIdentity, dorf1, dorf2) -> Village:
    return Village(
        id=identity.id,
        name=(scan_village_name(dorf1)),
        tribe=(identity_tribe(dorf2)),
        source_pits=(scan_village_source(dorf1)),
        buildings=(scan_village_center(dorf2)),
        building_queue=(scan_building_queue(dorf1)),
        **(scan_stock_bar(dorf1)),
        **(scan_production(dorf1))
    )


def _extract_number(entry, css_class: str) -> int:
    """Extract and parse a number value from HTML element."""
    element = entry.select_one(css_class)
    if not element:
        raise ValueError(f"Element missing {css_class}")

    return _parse_number(element.get_text())


def _parse_village_entry(entry) -> VillageIdentity:
    """Parse a single village entry from HTML element."""
    village_id = entry.get('data-did')
    if not village_id:
        raise ValueError("Village entry missing data-did attribute")

    name = _extract_text(entry, '.name')
    coordinate_x = _extract_number(entry, '.coordinateX')
    coordinate_y = _extract_number(entry, '.coordinateY')

    return VillageIdentity(
        id=int(village_id),
        name=name,
        coordinate_x=coordinate_x,
        coordinate_y=coordinate_y
    )


def scan_village_list(html: str) -> list[VillageIdentity]:
    """Parse village names and coordinates from HTML string."""
    soup = BeautifulSoup(html, HTML_PARSER)
    village_entries = soup.select('.villageList .listEntry.village')
    return [_parse_village_entry(entry) for entry in village_entries]

def scan_account_info(html: str) -> Account:
    soup = BeautifulSoup(html, HTML_PARSER)

    # Extract server speed from title
    server_speed = 1.0
    title_text = soup.title.string if soup.title else ""
    match = re.search(r'x(\d+)', title_text)
    if match:
        server_speed = float(match.group(1))

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
        server_speed=server_speed,
        when_beginners_protection_expires=beginners_expires
    )

def _is_hero_available(html: str) -> bool:
    """Check if hero is available for adventures."""
    soup = BeautifulSoup(html, HTML_PARSER)
    hero_state = soup.select_one(".heroState")

    if not hero_state:
        # If no heroState element found, assume hero is available
        return True

    state_text = clean_inner_text(hero_state)

    # Hero is available only if they are "currently in village"
    # Any other status (on the way, traveling, etc) means unavailable
    return "currently in village" in state_text


def _parse_hero_inventory(inventory_html: str) -> dict:
    """Parse hero inventory (resources) from inventory HTML. Returns a dict or empty dict if not found."""
    if not inventory_html:
        return {}
    inv_soup = BeautifulSoup(inventory_html, HTML_PARSER)
    hero_items = inv_soup.select_one(".heroItems")
    inventory = {}
    if hero_items:
        resource_map = {
            "item145": "lumber",
            "item146": "clay",
            "item147": "iron",
            "item148": "crop"
        }
        for item_class, resource in resource_map.items():
            item_div = hero_items.select_one(f".item.{item_class}")
            if item_div:
                parent = item_div.find_parent("div", class_="heroItem")
                if parent:
                    count_div = parent.select_one(".count")
                    if count_div:
                        inventory[resource] = _parse_number_value(count_div.get_text())
    return inventory

def scan_hero_info(hero_html: str, inventory_html: str = None) -> HeroInfo:
    soup = BeautifulSoup(hero_html, HTML_PARSER)
    value_elements = (_get_item_or_raise_error(soup, ".stats", "Hero stats container not found")
                       .select(".value"))
    if len(value_elements) < 2:
        raise ValueError("Not enough stats values found for hero info")

    health = _parse_number_value(clean_inner_text(value_elements[0]).replace('%', ''))
    experience = _parse_number_value(clean_inner_text(value_elements[1]))
    adventure_button = _get_item_or_raise_error(soup, "a.adventure", "Adventure button not found")
    adventures = _parse_adventure_number(adventure_button)
    is_available = _is_hero_available(hero_html)
    inventory = _parse_hero_inventory(inventory_html)
    points_available = _parse_available_attribute_points(soup)

    return HeroInfo(
        health=health,
        experience=experience,
        adventures=adventures,
        is_available=is_available,
        points_available=points_available,
        inventory=inventory
    )

def _parse_adventure_number(adventure_button: Tag) -> int:
    contant = adventure_button.select_one('div.content')
    if contant is None:
        return 0
    return _parse_number_value(contant)

def _parse_available_attribute_points(soup: BeautifulSoup) -> int:
    points_elem = soup.select_one(".pointsAvailable")
    if not points_elem:
        return 0
    return _parse_number_value(points_elem.get_text())

def is_reward_available(html: str) -> bool:
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

