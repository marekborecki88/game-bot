import os
import re
from pathlib import Path
from typing import Optional, Any

import yaml
from dotenv import load_dotenv

from src.domain.config import Config, HeroConfig, HeroAdventuresConfig, HeroResourcesConfig, AttributeAllocation, \
    LogicConfig, Strategy, DriverConfig

CONFIG_FILENAME = "config.yaml"

def find_config_path() -> str:
    """Find the most appropriate config.yaml path.

    Order of precedence:
    1. Explicit path passed in (config_path)
    2. CONFIG_PATH environment variable (if set and file exists)
    3. ./config.yaml in current working directory
    4. Search upward from current working directory for config.yaml
    5. config.yaml next to the installed package (fallback when running from source tree)

    Raises FileNotFoundError if no config file is found.
    """

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

# Helper to convert YAML format keys (hyphenated) to AttributeAllocation
def _parse_attribute_allocation(raw_dict: dict[str, int]) -> AttributeAllocation:
    """Convert raw YAML dict with hyphenated keys to AttributeAllocation."""
    key_map = {
        "fight": "fighting_strength",
        "fighting_strength": "fighting_strength",
        "fighting-strength": "fighting_strength",
        "power": "fighting_strength",
        "off": "off_bonus",
        "off_bonus": "off_bonus",
        "off-bonus": "off_bonus",
        "def": "def_bonus",
        "def_bonus": "def_bonus",
        "def-bonus": "def_bonus",
        "resources": "production_points",
        "production": "production_points",
        "production_points": "production_points",
        "production-points": "production_points",
    }

    normalized = {}
    for key, value in raw_dict.items():
        if not isinstance(value, int) or value < 0:
            continue
        canonical = key_map.get(key)
        if canonical is None:
            continue
        normalized[canonical] = normalized.get(canonical, 0) + value

    return AttributeAllocation(
        fighting_strength=normalized.get("fighting_strength", 0),
        off_bonus=normalized.get("off_bonus", 0),
        def_bonus=normalized.get("def_bonus", 0),
        production_points=normalized.get("production_points", 0),
    )

def load(config_path: Optional[str] = None) -> "Config":
    file = _find_config(config_path)
    data = _read_config(file)

    if not isinstance(data, dict):
        raise ValueError(f"Parsed config file {config_path} does not contain a mapping")


    return _map_to_domain(data)


def _read_config(file: Path) -> dict[str, Any]:
    content = file.read_text()

    def replace_env_var(match: re.Match) -> str:
        var_name = match.group(1)
        return os.getenv(var_name, match.group(0))

    content = re.sub(r'\$\{(\w+)}', replace_env_var, content)

    data = yaml.safe_load(content)
    return data


def _find_config(config_path: str | None) -> Path:
    load_dotenv()

    if config_path:
        path = Path(config_path)
        if not path.is_file():
            raise FileNotFoundError(f"CONFIG_PATH is set but file not found: {config_path}")
        return path
    return Path(find_config_path())


def _map_to_domain(data: dict) -> Config:
    driver_config = DriverConfig(
        server_url=data.get('server_url'),
        user_login=data.get('user_login'),
        user_password=data.get('user_password'),
        headless=bool(data.get('headless')),
    )

    logic_config = LogicConfig(
        speed=int(data.get('speed', 1)),
        strategy=Strategy(data.get('strategy')) if data.get('strategy') else None,
        minimum_storage_capacity_in_hours=int(data.get('minimum_storage_capacity_in_hours', 24)),
        daily_quest_threshold=int(data.get('daily_quest_threshold', 50)),
    )

    hero_data = data.get('hero', {})
    hero_config = HeroConfig(
        adventures=HeroAdventuresConfig(
            minimal_health=int(hero_data.get('adventures', {}).get('minimal-health', 50)),
            increase_difficulty=bool(hero_data.get('adventures', {}).get('increase-difficulty', False)),
        ),
        resources=HeroResourcesConfig(
            support_villages=bool(hero_data.get('resources', {}).get('support-villages', False)),
            attributes_ratio=_parse_attribute_allocation(hero_data.get('resources', {}).get('attributes-ratio', {})),
            attributes_steps=_parse_attribute_allocation(hero_data.get('resources', {}).get('attributes-steps', {})),
        ),
    )

    return Config(
        log_level=data.get('log_level', 'INFO'),
        driver_config=driver_config,
        logic_config=logic_config,
        hero_config=hero_config,
    )
