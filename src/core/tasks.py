from dataclasses import dataclass
from typing import Any

from src.core.model.model import Village
from src.core.task import Task


@dataclass
class BuildTask(Task):
    village_name: str
    village_id: int
    building_id: int
    building_gid: int
    target_name: str
    target_level: int


@dataclass
class BuildNewTask(Task):
    village_name: str
    village_id: int
    building_id: int
    building_gid: int
    target_name: str


@dataclass
class HeroAdventureTask(Task):
    hero_info: Any


@dataclass
class AllocateAttributesTask(Task):
    points: int


@dataclass
class CollectDailyQuestsTask(Task):
    pass


@dataclass
class CollectQuestmasterTask(Task):
    village: Village



