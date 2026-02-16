# Economy Planning System

## Overview

The economy planning system balances village resource production with military unit training needs across three development stages: **early**, **mid**, and **advanced**.

## Architecture

### Base Strategy Class (`src/core/strategy/strategy.py`)

Contains general-purpose methods used by all strategy implementations:

- `estimate_village_development_stage(village: Village) -> str`
  - Determines development stage based on resource pit levels
  - Returns: `'early'`, `'mid'`, or `'advanced'`

- `estimate_resource_production_proportions(planned_units: dict[str, int]) -> dict[ResourceType, float]`
  - Calculates target resource proportions based on planned unit costs
  - Example: Legionnaires cost 120 lumber + 150 iron → increases lumber and iron proportions
  - Returns: Dictionary with ResourceType → proportion (sum = 1.0)

### DefendArmyPolicy Implementation (`src/core/strategy/defend_army_policy.py`)

Concrete implementation for defensive army strategy:

- `plan_economy_upgrades(village, planned_units) -> list[tuple[BuildingType, float]]`
  - Main entry point - routes to stage-specific methods
  - Returns sorted list of (BuildingType, priority) tuples

- `plan_economy_upgrades_early_stage(village) -> list[tuple[BuildingType, float]]`
- `plan_economy_upgrades_mid_stage(village, planned_units) -> list[tuple[BuildingType, float]]`
- `plan_economy_upgrades_advanced_stage(village, planned_units) -> list[tuple[BuildingType, float]]`

## Development Stages

### Early Stage
**Trigger:** Any primary resource pit (woodcutter/clay_pit/iron_mine) below level 5

**Phase 1 - Foundations:**
- Build all primary resource pits to level 2
- Upgrade main building to level 5
- Ensure warehouse/granary capacity for 12h production

**Phase 2 - Growth:**
- Upgrade crop only if free_crop ratio < 0.1 (insufficient for other buildings)
- Upgrade all primary pits to level 5
- Maintain storage capacity

**Priority Order:**
```
1. Primary pits level 1→2 (high priority)
2. Main building level 1→5 (medium priority)
3. Primary pits level 2→5 (medium priority)
4. Crop (low priority, only if needed)
```

### Mid Stage
**Trigger:** All primary pits ≥ level 5

**Goals:**
- Continue upgrading primary pits (towards village max: 10 or 12)
- Build/upgrade secondary production buildings (sawmill, brickyard, iron_foundry)
- Adjust production proportions based on planned units

**Unit-Specific Optimization:**

| Unit | Lumber | Clay | Iron | Crop | Strategy |
|------|--------|------|------|------|----------|
| Legionnaire | 120 | 100 | 150 | 30 | Prioritize iron mines & iron foundry |
| Phalanx | 100 | 130 | 55 | 30 | Prioritize clay pits & brickyard |

**Priority Calculation:**
- Base priority = 500 (primary pits) or 300 (secondary buildings)
- Adjusted by resource proportion: `priority += (proportion * 300)`
- Higher proportion resource types get higher priority

**Example:**
For Legionnaire (iron=37.5%):
- Iron mine: 500 + (0.375 * 300) = 612.5
- Woodcutter: 500 + (0.30 * 300) = 590
- Clay pit: 500 + (0.25 * 300) = 575

### Advanced Stage
**Trigger:** At least one resource type fully developed (all pits at max + secondary at level 5+)

**Goals:**
- Specialize production based on planned units
- Maximize secondary buildings
- Only upgrade primary pits if resource proportion > 30%

**Priority Logic:**
1. Secondary buildings (sawmill, brickyard, iron_foundry) to max level
2. Primary pits only if proportion > 30%
3. Crop to comfortable level (low priority)

**Example Advanced Strategy:**
For Legionnaire production (iron=37.5% > 30%):
- Iron mines: will continue to be upgraded
- Iron foundry: prioritized to level 5
- Woodcutter/sawmill: may be skipped or lower priority
- Clay pit/brickyard: may be skipped or lower priority

## Resource Proportion Estimation

### Calculation Method

For each planned unit, extract costs and weight by quantity:

```
Total Lumber = Sum of (unit.costs.lumber × quantity) for all unit types
Total Clay   = Sum of (unit.costs.clay × quantity) for all unit types
Total Iron   = Sum of (unit.costs.iron × quantity) for all unit types
Total Crop   = Sum of (unit.costs.crop × quantity) for all unit types

Total = Total Lumber + Total Clay + Total Iron + Total Crop

Proportions:
  Lumber Proportion = Total Lumber / Total
  Clay Proportion   = Total Clay / Total
  Iron Proportion   = Total Iron / Total
  Crop Proportion   = Total Crop / Total
```

### Balanced Proportions (No Units Specified)

When no planned units are provided, default to balanced:
- All resources: 25% each

### Examples

**Legionnaire (120 lumber, 100 clay, 150 iron, 30 crop per unit):**
- Total cost: 400
- Proportions: lumber=30%, clay=25%, iron=37.5%, crop=7.5%

**Phalanx (100 lumber, 130 clay, 55 iron, 30 crop per unit):**
- Total cost: 315
- Proportions: lumber=31.7%, clay=41.3%, iron=17.5%, crop=9.5%

**Mixed (50 Legionnaires + 50 Phalanx):**
- 50 × [120,100,150,30] + 50 × [100,130,55,30]
- = [50×220, 50×230, 50×205, 50×60]
- = [11000, 11500, 10250, 3000]
- Proportions: lumber=33.9%, clay=35.5%, iron=31.6%, crop=-1%

## Integration with DefendArmyPolicy

### Usage Example

```python
from src.core.strategy.defend_army_policy import DefendArmyPolicy

policy = DefendArmyPolicy(logic_config, hero_config)

# Get economy upgrades for a village
planned_units = {"Legionnaire": 100}  # Plan to train 100 Legionnaires
upgrades = policy.plan_economy_upgrades(village, planned_units)

# Returns: [(BuildingType.IRON_MINE, 612.5), (BuildingType.WOODCUTTER, 590), ...]
for building_type, priority in upgrades:
    print(f"Upgrade {building_type.name} (priority: {priority})")
```

### Integration with Job Planner

The planning system is designed to feed into a job scheduler:

1. Get village development stage
2. Call `plan_economy_upgrades()` to get prioritized list
3. For each suggested upgrade:
   - Check if building can be built/upgraded
   - Calculate cost and time
   - Add to job queue if resources available
   - Consider resource transportation time

## Testing

Test file: `tests/core/test_economy_planning.py`

**Test Coverage:**
- Early stage detection and planning
- Mid stage planning with unit-specific optimization
- Advanced stage planning with specialization
- Resource proportion calculation
- Stage routing logic
- Priority sorting validation

Run tests:
```bash
poetry run pytest tests/core/test_economy_planning.py -v
```

## Future Enhancements

1. **Storage capacity planning** - Ensure warehouse/granary can hold full production
2. **Merchant planning** - Calculate merchant needs for resource transport
3. **Capital specialization** - Different strategies for capital vs normal villages
4. **Multiple villages** - Optimize production across all villages together
5. **Market-aware planning** - Consider marketplace prices for resource balance
6. **Custom unit mixes** - Support more than 2 unit types in proportion calculation
