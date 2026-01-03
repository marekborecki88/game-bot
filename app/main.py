import time

from playwright.sync_api import sync_playwright, Page

from app.config import load_config, Config
from app.login import login
from app.scan import scan, scan_building_queue


def waitUntilBuildingQueueIsEmpty(page: Page, check_interval: int = 10):
    """Wait until the building queue is empty.

    Args:
        page: The Playwright page object
        check_interval: How often to check the queue in seconds (default: 10)
    """
    print("Waiting for building queue to become empty...")

    while True:
        building_queue = scan_building_queue(page)

        if len(building_queue) == 0:
            print("Building queue is empty!")
            break

        # Calculate total remaining time
        total_time = sum(job.time_remaining for job in building_queue)
        print(f"Building queue has {len(building_queue)} job(s), total time remaining: {total_time} seconds")

        # Wait for the specified interval before checking again
        time.sleep(check_interval)

jobs = [
    {"village_name": "Sodoma", "id": 1},
    {"village_name": "Sodoma", "id": 3},
    {"village_name": "Sodoma", "id": 1},
    {"village_name": "Sodoma", "id": 3},
    {"village_name": "Sodoma", "id": 14},
    {"village_name": "Sodoma", "id": 17},
    {"village_name": "Sodoma", "id": 5},
    {"village_name": "Sodoma", "id": 16},
    {"village_name": "Sodoma", "id": 18},
]

with sync_playwright() as p:
    config: Config = load_config("../config.yaml")
    browser, page = login(p, config)

    for job in jobs:
        account = scan(page, config)
        print(account)
        waitUntilBuildingQueueIsEmpty(page)
        account.build(page, config, **job)

    browser.close()