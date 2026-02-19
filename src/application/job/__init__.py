"""Job implementations for the game bot."""

from src.application.job.job import Job, JobStatus
from src.application.job.build_job import BuildJob
from src.application.job.build_new_job import BuildNewJob
from src.application.job.hero_adventure_job import HeroAdventureJob
from src.application.job.allocate_attributes_job import AllocateAttributesJob
from src.application.job.collect_daily_quests_job import CollectDailyQuestsJob
from src.application.job.collect_questmaster_job import CollectQuestmasterJob
from src.application.job.planning_job import PlanningJob
from src.application.job.found_new_village_job import FoundNewVillageJob
from src.application.job.scheduler import ScheduledJobQueue

__all__ = [
    "Job",
    "JobStatus",
    "BuildJob",
    "BuildNewJob",
    "HeroAdventureJob",
    "AllocateAttributesJob",
    "CollectDailyQuestsJob",
    "CollectQuestmasterJob",
    "PlanningJob",
    "FoundNewVillageJob",
    "ScheduledJobQueue",
]
