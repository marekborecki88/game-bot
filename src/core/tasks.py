from dataclasses import dataclass
from typing import Any

from src.core.model.model import Village
from src.core.task import Task


@dataclass(frozen=True)
class BuildTask(Task):
    village_name: str
    village_id: int
    building_id: int
    building_gid: int
    target_name: str
    target_level: int


@dataclass(frozen=True)
class BuildNewTask(Task):
    village_name: str
    village_id: int
    building_id: int
    building_gid: int
    target_name: str


@dataclass(frozen=True)
class HeroAdventureTask(Task):
    hero_info: Any


@dataclass(frozen=True)
class AllocateAttributesTask(Task):
    points: int


@dataclass(frozen=True)
class CollectDailyQuestsTask(Task):
    pass


@dataclass(frozen=True)
class CollectQuestmasterTask(Task):
    village: Village

