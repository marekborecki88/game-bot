import time
import random

from playwright.sync_api import Page

# def waitUntilBuildingQueueIsEmpty(page: Page):
#     """Wait until the building queue is empty.
#
#     Args:
#         page: The Playwright page object
#         check_interval: How often to check the queue in seconds (default: 10)
#     """
#     print("Waiting for building queue to become empty...")
#
#     i=0
#
#     while True:
#         building_queue = scan_building_queue(page)
#
#         if len(building_queue) == 0:
#             print("Building queue is empty!")
#             break
#
#         # Calculate total remaining time
#         total_time = sum(job.time_remaining for job in building_queue)
#
#         # Wait for a random interval before checking again
#         check_interval = random.randint(10, 120)
#         if i%10==0:
#             print(f"Building queue has {len(building_queue)} job(s), total time remaining: {total_time} seconds")
#             print(f"Waiting {check_interval} seconds before next check...")
#         else:
#             print(".", end="", flush=True)
#         i+=1
#
#         time.sleep(check_interval)
