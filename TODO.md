# MAJOR TODOs
1. There should be defined policies for developing villages:
    - Balanced
    - Resource oriented
    - Military oriented (Defense/Offense)
    - Supporter (just support other account)
    - Would be great to be able to define custom policies in configuration


# MINOR TODOs
1. Introduce Interfaces to revert dependencies
2. add sending hero to adventure
3. add posibility to use resources from hero's inventory

ISSUES:

1. improve logs
       2026-01-14 15:07:29,069 INFO     src.core.bot - Building in village: GOMORA, id: 21, type: unknown
2. remove dict from job execution
       use dedicated type, add abstraction to reflect different type of jobs like building, sending troops, sending merchants, etc.
3. for some reason logic_engine decide to send hero to adventure even when there is no adventure available
   logs like "Hero adventure not started (no button found or driver failed)"
4. ____