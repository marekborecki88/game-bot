from dataclasses import dataclass

from src.core.model.model import HeroInfo, Resources
from src.core.model.village import Village


@dataclass
class GameState:
    account: "Account"
    villages: list[Village]
    hero_info: HeroInfo

    @property
    def calculate_global_resources(self) -> Resources:
        total_resources = Resources()
        for village in self.villages:
            total_resources += village.resources
        total_resources += self.hero_info.hero_inventory_resource()
        return total_resources
