import pytest
from bs4 import BeautifulSoup

from src.core.model.model import VillageBasicInfo, ResourcePit, ResourceType, Building, BuildingType, BuildingJob, Account, \
    Tribe, HeroInfo, HeroAttributes, BuildingContract, Resources, BuildingQueue, IncomingAttackInfo
from src.core.model.village import Village
from src.scan_adapter.scanner_adapter import Scanner
from tests.scanner_adapter.html_utils import HtmlUtils


@pytest.fixture
def dorf1_html():
    return HtmlUtils.load("dorf1.html")


@pytest.fixture
def dorf2_html():
    return HtmlUtils.load("dorf2.html")


@pytest.fixture
def hero_attributes_html():
    return HtmlUtils.load("hero_attributes.html")


@pytest.fixture
def inventory_html():
    return HtmlUtils.load("inventory.html")


@pytest.fixture
def village_list_html():
    return HtmlUtils.load("upgradeBuilding.html")


@pytest.fixture
def movements_html():
    return HtmlUtils.load("movements.html")


def test_scan_village_list(dorf1_html):
    # Given
    scanner = Scanner(server_speed=1)

    # When
    result = scanner.scan_village_list(dorf1_html)

    # Then
    expected = [
        VillageBasicInfo(id=50275, name="SODOMA", coordinate_x=1, coordinate_y=146),
        VillageBasicInfo(id=50281, name="GOMORA", coordinate_x=2, coordinate_y=146),
        VillageBasicInfo(id=50287, name="New village", coordinate_x=2, coordinate_y=147)
    ]
    assert result == expected

def test_scan_village_source(dorf1_html):
    # Given
    scanner = Scanner(server_speed=1)

    # When
    result = scanner.scan_village_source(dorf1_html)

    # Then
    expected = [
        ResourcePit(id=1, type=ResourceType.LUMBER, level=8),
        ResourcePit(id=2, type=ResourceType.CROP, level=10),
        ResourcePit(id=3, type=ResourceType.CROP, level=0),
        ResourcePit(id=4, type=ResourceType.LUMBER, level=5),
        ResourcePit(id=5, type=ResourceType.CLAY, level=5),
        ResourcePit(id=6, type=ResourceType.CLAY, level=6),
        ResourcePit(id=7, type=ResourceType.IRON, level=5),
        ResourcePit(id=8, type=ResourceType.CROP, level=3),
        ResourcePit(id=9, type=ResourceType.CROP, level=5),
        ResourcePit(id=10, type=ResourceType.IRON, level=2),
        ResourcePit(id=11, type=ResourceType.IRON, level=5),
        ResourcePit(id=12, type=ResourceType.CROP, level=4),
        ResourcePit(id=13, type=ResourceType.CROP, level=5),
        ResourcePit(id=14, type=ResourceType.LUMBER, level=8),
        ResourcePit(id=15, type=ResourceType.CROP, level=3),
        ResourcePit(id=16, type=ResourceType.CLAY, level=7),
        ResourcePit(id=17, type=ResourceType.LUMBER, level=5),
        ResourcePit(id=18, type=ResourceType.CLAY, level=9)
    ]

    assert result == expected


def test_scan_village_center(dorf2_html):
    # Given
    scanner = Scanner(server_speed=1)

    # When
    result = scanner.scan_village_center(dorf2_html)

    # Then
    expected = [
        Building(id=20, type=BuildingType.WAREHOUSE, level=7),
        Building(id=21, type=BuildingType.GRANARY, level=11),
        Building(id=26, type=BuildingType.MAIN_BUILDING, level=3),
        Building(id=39, type=BuildingType.RALLY_POINT, level=1)
    ]

    assert result == expected


def test_scan_village_name(dorf1_html):
    # Given
    scanner = Scanner(server_speed=1)

    # When
    result = scanner.scan_village_basic_info(dorf1_html)

    # Then
    assert result == VillageBasicInfo(id=50287, name="New village", coordinate_x=2, coordinate_y=147)

def test_scan_stock_bar(dorf1_html):
    # Given
    scanner = Scanner(server_speed=1)

    # When
    result = scanner.scan_stock_bar(dorf1_html)

    # Then
    expected = {
        "lumber": 5636,
        "clay": 5475,
        "iron": 5844,
        "crop": 14284,
        "free_crop": 1503,
        "warehouse_capacity": 6300,
        "granary_capacity": 14400,
    }
    assert result == expected


def test_scan_production(dorf1_html):
    # Given
    scanner = Scanner(server_speed=1)

    # When
    result = scanner.scan_production(dorf1_html)

    # Then
    expected = {
        "lumber_hourly_production": 920,
        "clay_hourly_production": 1040,
        "iron_hourly_production": 690,
        "crop_hourly_production": 1504,
        "free_crop_hourly_production": 1503
    }
    assert result == expected


def test_scan_village(dorf1_html, dorf2_html):
    # Given
    scanner = Scanner(server_speed=1)
    identity = VillageBasicInfo(id=50287, name="New village", coordinate_x=2, coordinate_y=147)

    # When
    result = scanner.scan_village(identity, dorf1_html, dorf2_html)

    # Then
    expected = Village(
        id=50287,
        name="New village",
        tribe=result.tribe,
        resources=Resources(lumber=5636, clay=5475, iron=5844, crop=14284),
        coordinates=(2, 147),
        free_crop=1503,
        warehouse_capacity=6300,
        granary_capacity=14400,
        lumber_hourly_production=920,
        clay_hourly_production=1040,
        iron_hourly_production=690,
        crop_hourly_production=1504,
        free_crop_hourly_production=1503,
        resource_pits=result.resource_pits,
        buildings=result.buildings,
        building_queue=result.building_queue,
        is_under_attack=False,
        incoming_attack_count=0,
        next_attack_seconds=None,
    )
    assert result == expected


def test_scan_building_queue(dorf1_html):
    # Given
    scanner = Scanner(server_speed=1)

    # When
    result = scanner.scan_building_queue(dorf1_html, parallel_building_allowed=True)

    # Then
    expected = BuildingQueue(
        parallel_building_allowed=True,
        in_jobs=[
            BuildingJob(
                building_name='Main Building',
                target_level=2,
                time_remaining=98
            ),
            BuildingJob(
                building_name='Main Building',
                target_level=3,
                time_remaining=628
            )
        ],
        out_jobs=[]
    )
    assert result == expected


def test_scan_account_info(dorf1_html):
    # Given
    scanner = Scanner(server_speed=1)

    # When
    result = scanner.scan_account_info(dorf1_html)

    # Then
    expected = Account(
        when_beginners_protection_expires=42778
    )
    assert result == expected


def test_identity_tribe(dorf2_html):
    # Given
    scanner = Scanner(server_speed=1)

    # When
    result = scanner.identity_tribe(dorf2_html)

    # Then
    assert result == Tribe.ROMANS


def test_scan_hero_info(hero_attributes_html, inventory_html):
    # Given
    scanner = Scanner(server_speed=1)

    # When
    result = scanner.scan_hero_info(hero_attributes_html, inventory_html)

    # Then
    expected = HeroInfo(
        health=90,
        experience=16594,
        adventures=83,
        is_available=True,
        hero_attributes=HeroAttributes(
            fighting_strength=0,
            off_bonus=0,
            def_bonus=68,
            production_points=36,
        ),
        inventory={
            "lumber": 616,
            "clay": 34210,
            "iron": 31376,
            "crop": 174257
        }
    )
    assert result == expected


def test_scan_hero_info_with_attribute_points(inventory_html):
    # Given
    scanner = Scanner(server_speed=1)
    html = HtmlUtils.load("hero_attributes_with_points.html")

    # When
    result = scanner.scan_hero_info(html, inventory_html)

    # Then
    assert result.points_available == 4


def test_scan_hero_info_without_attribute_points(hero_attributes_html, inventory_html):
    # Given
    scanner = Scanner(server_speed=1)

    # Ensure existing fixture doesn't report attribute points
    result = scanner.scan_hero_info(hero_attributes_html, inventory_html)
    assert result.points_available == 0


def test_scan_hero_without_adventures():
    # Given
    scanner = Scanner(server_speed=1)
    html = """
           <a id="button6977c92fb7cdd" class="layoutButton buttonFramed withIcon round adventure green    "
              href="/hero/adventures">
               <svg viewBox="0 0 19.75 20" class="adventure"></svg>
           </a>
    """
    tag = BeautifulSoup(html, "html.parser")

    # When
    result = scanner._parse_adventure_number(tag)

    # Then
    assert result == 0


def test_scan_hero_with_adventures():
    # Given
    scanner = Scanner(server_speed=1)
    html = """
           <a id="button6977c92fb7cdd" class="layoutButton buttonFramed withIcon round adventure green    "
              href="/hero/adventures">
               <div class="content">5</div>
           </a>
    """
    tag = BeautifulSoup(html, "html.parser")

    # When
    result = scanner._parse_adventure_number(tag)

    # Then
    assert result == 5


def test_scan_contract():
    # Given
    scanner = Scanner(server_speed=1)
    html = """
           <div id="contract_building10" class="buildingWrapper">
               <div class="upgradeBuilding">
                   <div id="contract" class="contractWrapper">
                       <div class="inlineIconList resourceWrapper">
                           <div class="inlineIcon resource"><i class="r1Big"></i><span class="value value">130</span>
                           </div>
                           <div class="inlineIcon resource"><i class="r2Big"></i><span class="value value">160</span>
                           </div>
                           <div class="inlineIcon resource"><i class="r3Big"></i><span class="value value">90</span>
                           </div>
                           <div class="inlineIcon resource"><i class="r4Big"></i><span class="value value">40</span>
                           </div>
                           <div class="inlineIcon resource"><i class="cropConsumptionBig"></i><span class="value value">1</span>
                           </div>
                       </div>
                       <div class="upgradeBlocked">
                       </div>
                   </div>
                   <div class="upgradeButtonsContainer section2Enabled">
                       <div class="section1">
                           <div class="inlineIcon duration">
                               <div class="iconWrapper"><i class="clock_medium"></i></div>
                               <span class="value ">0:33:20</span>
                           </div>
                       </div>
                   </div>
               </div>
           </div>
           """

    soup = BeautifulSoup(html, "html.parser")
    tag = soup.select_one("#contract_building10")
    if tag is None:
        pytest.fail("Failed to parse test HTML for contract scanning.")

    # When
    result = scanner.scan_new_building_contract(tag)

    # Then
    expected = BuildingContract(
        Resources(lumber=130, clay=160, iron=90, crop=40),
        crop_consumption=1,
    )
    assert result == expected


def test_scan_incoming_attacks(movements_html: str) -> None:
    # Given
    scanner = Scanner(server_speed=1)

    # When
    result = scanner.scan_incoming_attacks(movements_html)

    # Then
    assert result == IncomingAttackInfo(attack_count=1, next_attack_seconds=402)
