import re

from bs4 import BeautifulSoup, Tag
from src.core.model.Village import BuildingType, Village, SourcePit, SourceType, Building, BuildingJob, VillageIdentity

HTML_PARSER = 'html.parser'


def _parse_resource_value(text: str) -> int:
    """Parse resource value from text, removing UNICODE markers and formatting."""
    cleaned = "".join(c for c in text if c.isdigit())
    return int(cleaned) if cleaned else 0


def clean_inner_text(html) -> str:
    return html.inner_text().strip()


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
        type=(BuildingType(gid)),
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
    warehouse_capacity = _parse_resource_value(
        stock_bar.select_one(".warehouse .capacity .value").get_text()
    )

    # Parse granary capacity
    granary_capacity = _parse_resource_value(
        stock_bar.select_one(".granary .capacity .value").get_text()
    )

    # Parse resources
    lumber = _parse_resource_value(stock_bar.select_one("#l1").get_text())
    clay = _parse_resource_value(stock_bar.select_one("#l2").get_text())
    iron = _parse_resource_value(stock_bar.select_one("#l3").get_text())
    crop = _parse_resource_value(stock_bar.select_one("#l4").get_text())
    free_crop = _parse_resource_value(stock_bar.select_one("#stockBarFreeCrop").get_text())

    return {
        "lumber": lumber,
        "clay": clay,
        "iron": iron,
        "crop": crop,
        "free_crop": free_crop,
        "warehouse_capacity": warehouse_capacity,
        "granary_capacity": granary_capacity,
    }


def scan_building_queue(html: str) -> list[BuildingJob]:
    """Scan the building queue from the current page."""
    soup = BeautifulSoup(html, HTML_PARSER)
    building_queue = []

    queue_container = soup.select_one(".buildingList")
    if not queue_container:
        return building_queue

    queue_items = queue_container.select("ul li")

    for item in queue_items:
        name_elem = item.select_one(".name")
        if not name_elem:
            continue

        name_text = name_elem.get_text(separator=" ", strip=True)
        level_match = re.search(r'Level\s+(\d+)', name_text)
        target_level = int(level_match.group(1)) if level_match else 0

        # Extract remaining time in seconds
        timer_elem = item.select_one(".timer")
        time_remaining = 0
        if timer_elem:
            timer_value = timer_elem.get('value')
            if timer_value and timer_value.isdigit():
                time_remaining = int(timer_value)

        building_queue.append(BuildingJob(
            building_id=0,  # Cannot easily determine building_id from this view
            target_level=target_level,
            time_remaining=time_remaining,
        ))

    return building_queue


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
        source_type = next((st for st in SourceType if st.value == gid), None)

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


def scan_village(identity: VillageIdentity, dorf1, dorf2) -> Village:
    return Village(
        id=identity.id,
        name=(scan_village_name(dorf1)),
        source_pits=(scan_village_source(dorf1)),
        buildings=(scan_village_center(dorf2)),
        building_queue=(scan_building_queue(dorf1)),
        **(scan_stock_bar(dorf1))
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


