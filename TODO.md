# MAJOR TODOs
1. There should be defined policies for developing villages:
    - Balanced
    - Resource oriented
    - Military oriented (Defense/Offense)
    - Supporter (just support other account)
    - Would be great to be able to define custom policies in configuration


# MINOR TODOs
1. Introduce Interfaces to revert dependencies
2. add possibility to use resources from hero's inventory
3. add possibility to switch hero resource production bonus depend on current village needs
4. click close window after operation on hero's inventory, hero's attributes, collecting daily reavards, collecting rewards from quest master
5. watch commercials to improve diffucult level of adventure

ISSUES:

1. remove dict from job execution
       use dedicated type, add abstraction to reflect different type of jobs like building, sending troops, sending merchants, etc.
2. for some reason logic_engine decide to send hero to adventure even when there is no adventure available
   logs like "Hero adventure not started (no button found or driver failed)"
3. fix loosing internet connection issue
    "Planning failed: Page.goto: net::ERR_NAME_NOT_RESOLVED at ..."
