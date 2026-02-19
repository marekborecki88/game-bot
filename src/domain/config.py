from dataclasses import dataclass
from enum import Enum


class Strategy(Enum):
    BALANCED_ECONOMIC_GROWTH = "balanced_economic_growth"
    DEFEND_ARMY = "defend_army"


@dataclass(frozen=True)
class DriverConfig:
    """Configuration for the browser driver and login."""
    server_url: str
    user_login: str
    user_password: str
    headless: bool


@dataclass(frozen=True)
class HeroAdventuresConfig:
    """Configuration for hero adventures."""
    minimal_health: int = 1
    increase_difficulty: bool = False


@dataclass(frozen=True)
class AttributeAllocation:
    """Attribute point allocation configuration."""
    fighting_strength: int = 0
    off_bonus: int = 0
    def_bonus: int = 0
    production_points: int = 0

    def __post_init__(self):
        for name, value in self.to_dict().items():
            if not 0 <= value <= 100:
                raise ValueError(f"Attribute {name} must be between 0 and 100, got: {value}")

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary for processing."""
        return {
            "fighting_strength": self.fighting_strength,
            "off_bonus": self.off_bonus,
            "def_bonus": self.def_bonus,
            "production_points": self.production_points,
        }


@dataclass(frozen=True)
class HeroResourcesConfig:
    """Configuration for hero resource gathering."""
    support_villages: bool = False
    attributes_ratio: AttributeAllocation = AttributeAllocation(production_points=100)
    attributes_steps: AttributeAllocation = AttributeAllocation()

@dataclass(frozen=True)
class HeroConfig:
    """Configuration for hero behavior and attributes."""
    adventures: HeroAdventuresConfig = HeroAdventuresConfig()
    resources: HeroResourcesConfig = HeroResourcesConfig()


@dataclass(frozen=True)
class LogicConfig:
    """Configuration for the bot logic and planning."""
    speed: int
    strategy: Strategy | None
    minimum_storage_capacity_in_hours: int = 24  # Default value if not specified
    daily_quest_threshold: int = 50  # Minimum points required to collect daily quest reward


@dataclass(frozen=True)
class Config:
    """Main configuration containing log level and nested config objects."""
    log_level: str
    driver_config: DriverConfig
    logic_config: LogicConfig
    hero_config: HeroConfig


