"""Job implementations for the game bot."""

from src.core.job.job import Job, JobStatus
from src.core.job.build_job import BuildJob
from src.core.job.build_new_job import BuildNewJob
from src.core.job.hero_adventure_job import HeroAdventureJob
from src.core.job.allocate_attributes_job import AllocateAttributesJob
from src.core.job.collect_daily_quests_job import CollectDailyQuestsJob
from src.core.job.collect_questmaster_job import CollectQuestmasterJob

__all__ = [
    "Job",
    "JobStatus",
    "BuildJob",
    "BuildNewJob",
    "HeroAdventureJob",
    "AllocateAttributesJob",
    "CollectDailyQuestsJob",
    "CollectQuestmasterJob",
]
