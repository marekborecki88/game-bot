from dataclasses import dataclass

from app.config import Config
from app.model.Village import Village
from playwright.sync_api import Page, Locator


@dataclass
class Account:
    villages: list[Village]

    def build(self, page: Page, config: Config, village_name: str, id: int):
        village = next((v for v in self.villages if v.name == village_name), None)
        if not village:
            return

        village.build(page, config, id)


