import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

CONFIG_FILENAME = "config.yaml"


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
    minimal_health: int
    increase_difficulty: bool


@dataclass(frozen=True)
class HeroResourcesConfig:
    """Configuration for hero resource gathering."""
    support_villages: bool
    attributes_ratio: dict[str, int]
    attributes_steps: dict[str, int]


@dataclass(frozen=True)
class HeroConfig:
    """Configuration for hero behavior and attributes."""
    adventures: HeroAdventuresConfig
    resources: HeroResourcesConfig


@dataclass(frozen=True)
class LogicConfig:
    """Configuration for the bot logic and planning."""
    speed: int
    strategy: Strategy | None
    minimum_storage_capacity_in_hours: int = 24  # Default value if not specified


@dataclass
class Config:
    """Main configuration containing log level and nested config objects."""
    log_level: str
    driver_config: DriverConfig
    logic_config: LogicConfig
    hero_config: HeroConfig

    @classmethod
    def find_config_path(cls, config_path: Optional[str] = None) -> str:
        """Find the most appropriate config.yaml path.

        Order of precedence:
        1. Explicit path passed in (config_path)
        2. CONFIG_PATH environment variable (if set and file exists)
        3. ./config.yaml in current working directory
        4. Search upward from current working directory for config.yaml
        5. config.yaml next to the installed package (fallback when running from source tree)

        Raises FileNotFoundError if no config file is found.
        """
        # 1. Explicit argument
        if config_path:
            path = Path(config_path)
            if path.is_file():
                return str(path)
            raise FileNotFoundError(f"CONFIG_PATH is set but file not found: {config_path}")

        # 2. Environment variable
        env_config_path = os.getenv("CONFIG_PATH")
        if env_config_path:
            path = Path(env_config_path)
            if path.is_file():
                return str(path)
            raise FileNotFoundError(f"CONFIG_PATH is set but file not found: {env_config_path}")

        # 3. cwd/CONFIG_FILENAME
        cwd_config = Path.cwd() / CONFIG_FILENAME
        if cwd_config.is_file():
            return str(cwd_config)

        # 4. Walk upward from CWD to root
        p = Path.cwd()
        for parent in (p, *p.parents):
            candidate = parent / CONFIG_FILENAME
            if candidate.is_file():
                return str(candidate)

        # 5. Package-relative (when running from source tree or installed package)
        package_config = Path(__file__).resolve().parents[1] / CONFIG_FILENAME
        if package_config.is_file():
            return str(package_config)

        raise FileNotFoundError(
            f"{CONFIG_FILENAME} not found. Set CONFIG_PATH, or place {CONFIG_FILENAME} in the current working "
            "directory or a parent directory."
        )

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Factory method: load a Config instance from a YAML file.

        If config_path is provided it will be used (and validated). Otherwise the
        discovery rules in `find_config_path` are applied. Environment variables
        are loaded from a `.env` file (load_dotenv) and substitution of ${VAR}
        tokens inside the YAML content is supported.
        """
        load_dotenv()

        if config_path:
            path = Path(config_path)
            if not path.is_file():
                raise FileNotFoundError(f"CONFIG_PATH is set but file not found: {config_path}")
            config_file = path
        else:
            config_file = Path(cls.find_config_path())

        content = config_file.read_text()

        def replace_env_var(match: re.Match) -> str:
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))

        content = re.sub(r'\$\{(\w+)}', replace_env_var, content)

        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError(f"Parsed config file {config_file} does not contain a mapping")

        driver_config = DriverConfig(
            server_url=data['server_url'],
            user_login=data['user_login'],
            user_password=data['user_password'],
            headless=bool(data['headless']),
        )

        logic_config = LogicConfig(
            speed=int(data['speed']),
            strategy=Strategy(data['strategy']) if 'strategy' in data else None,
            minimum_storage_capacity_in_hours=int(data.get('minimum_storage_capacity_in_hours', 24)),
        )

        hero_data = data.get('hero', {})
        hero_config = HeroConfig(
            adventures=HeroAdventuresConfig(
                minimal_health=int(hero_data.get('adventures', {}).get('minimal-health', 50)),
                increase_difficulty=bool(hero_data.get('adventures', {}).get('increase-difficulty', False)),
            ),
            resources=HeroResourcesConfig(
                support_villages=bool(hero_data.get('resources', {}).get('support-villages', False)),
                attributes_ratio=dict(hero_data.get('resources', {}).get('attributes-ratio', {})),
                attributes_steps=dict(hero_data.get('resources', {}).get('attributes-steps', {})),
            ),
        )

        return cls(
            log_level=data.get('log_level', 'INFO'),
            driver_config=driver_config,
            logic_config=logic_config,
            hero_config=hero_config,
        )


# Backwards-compatible helper (optional) - kept for other modules that may import load_config
def load_config(config_path: str) -> Config:
    """Compatibility wrapper around Config.load.

    Kept for callers that expect a module-level function taking the path.
    """
    return Config.load(config_path)
