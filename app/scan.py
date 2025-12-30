import re

from playwright.sync_api import Page

from app.config import Config
from app.model.Account import Account
from app.model.Village import Village, SourcePit, SourceType, Building, BuildingJob


def scan_village_list() -> list[str]:
    return ["dorf1"]


def scan_village_source(page: Page) -> list[SourcePit]:
    """Scan all resource fields from the village resource view."""

    # Wait for the resource field container to appear
    page.wait_for_selector("#resourceFieldContainer")

    container = page.locator("#resourceFieldContainer")
    resource_fields = container.locator("a")

    source_pits = []

    for i in range(resource_fields.count()):
        field = resource_fields.nth(i)
        class_attr = field.get_attribute("class") or ""

        # Skip if it's the village center
        if "villageCenter" in class_attr:
            continue

        gid_match = re.search(r'gid(\d+)', class_attr)
        if not gid_match:
            continue
        gid = int(gid_match.group(1))

        # Map gid to SourceType
        source_type = next((st for st in SourceType if st.value == gid), None)

        # Extract buildingSlot (field id)
        slot_match = re.search(r'buildingSlot(\d+)', class_attr)
        if not slot_match:
            continue
        field_id = int(slot_match.group(1))

        # Extract level
        level_match = re.search(r'level(\d+)', class_attr)
        level = int(level_match.group(1)) if level_match else 0

        source_pits.append(SourcePit(
            id=field_id,
            type=source_type,
            level=level,
        ))

    return source_pits


def scan_village_center(page: Page, config: Config) -> list[Building]:
    """Scan all buildings from the village center view."""
    from app.model.Village import Building, BuildingType

    page.goto(f"{config.server_url}/dorf2.php")
    page.wait_for_selector("#villageContent")

    container = page.locator("#villageContent")
    building_slots = container.locator("div.buildingSlot")

    buildings = []

    for i in range(building_slots.count()):
        slot = building_slots.nth(i)
        class_attr = slot.get_attribute("class") or ""

        # Extract gid (building type)
        gid_match = re.search(r'g(\d+)', class_attr)
        if not gid_match:
            continue
        gid = int(gid_match.group(1))

        # Skip empty slots (gid 0)
        if gid == 0:
            continue

        # Map gid to BuildingType
        building_type = next((bt for bt in BuildingType if bt.value == gid), None)

        # Extract building slot id
        slot_match = re.search(r'a(\d+)', class_attr)
        if not slot_match:
            continue
        building_id = int(slot_match.group(1))

        # Extract level from the level element
        level_elem = slot.locator(".labelLayer")
        level = 0
        if level_elem.count() > 0:
            level_text = level_elem.first.inner_text().strip()
            if level_text.isdigit():
                level = int(level_text)

        buildings.append(Building(
            id=building_id,
            type=building_type,
            level=level,
        ))

    return buildings


def scan_building_queue(page: Page) -> list[BuildingJob]:
    """Scan the building queue from the current page."""
    building_queue = []

    # Building queue is in .buildingList
    queue_container = page.locator(".buildingList")
    if queue_container.count() == 0:
        return building_queue

    queue_items = queue_container.locator("li")

    for i in range(queue_items.count()):
        item = queue_items.nth(i)

        # Extract building name and level from the text
        name_elem = item.locator(".name")
        if name_elem.count() == 0:
            continue

        name_text = name_elem.inner_text().strip()
        # Format: "Building Name Level X"
        level_match = re.search(r'(\d+)$', name_text)
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


def scan_stock_bar(page: Page) -> dict:
    stock_bar = page.locator("#stockBar")

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


def _parse_resource_value(text: str) -> int:
    """Parse resource value from text, removing unicode markers and formatting."""
    # Remove unicode left-to-right markers (U+202D, U+202C) and whitespace
    cleaned = text.replace('\u202d', '').replace('\u202c', '').strip()
    # Remove thousand separators (comma)
    cleaned = cleaned.replace(',', '')
    return int(cleaned)


def scan(page: Page, config: Config) -> Account:
    print("Scanning...")
    indices = scan_village_list()
    villages = []
    for index in indices:
        source_pits = scan_village_source(page)
        buildings = scan_village_center(page, config)
        building_queue = scan_building_queue(page)
        stock_data = scan_stock_bar(page)
        villages.append(Village(
            name=index,
            lumber=stock_data["lumber"],
            clay=stock_data["clay"],
            iron=stock_data["iron"],
            crop=stock_data["crop"],
            free_crop=stock_data["free_crop"],
            warehouse_capacity=stock_data["warehouse_capacity"],
            granary_capacity=stock_data["granary_capacity"],
            source_pits=source_pits,
            buildings=buildings,
            building_queue=building_queue,
        ))

    return Account(villages=villages)
