from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from src.core.model.model import VillageIdentity, SourcePit, SourceType, Building, BuildingType, BuildingJob, Account, Tribe, HeroInfo, Village
from src.scan_adapter.scanner import (
    scan_village_name,
    scan_stock_bar,
    scan_building_queue,
    scan_village_source,
    scan_village_center, scan_village_list,
    scan_production,
    scan_village,
    scan_account_info,
    identity_tribe,
    scan_hero_info,
    _parse_adventure_number
)
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


def test_scan_village_list(dorf1_html):

    # When
    result = scan_village_list(dorf1_html)

    # Then
    expected = [
        VillageIdentity(id=50275, name="SODOMA", coordinate_x=1, coordinate_y=146),
        VillageIdentity(id=50281, name="GOMORA", coordinate_x=2, coordinate_y=146),
        VillageIdentity(id=50287, name="New village", coordinate_x=2, coordinate_y=147)
    ]
    assert result == expected


def test_scan_village_source(dorf1_html):

    # When
    result = scan_village_source(dorf1_html)

    # Then
    expected = [
        SourcePit(id=1, type=SourceType.LUMBER, level=8),
        SourcePit(id=2, type=SourceType.CROP, level=10),
        SourcePit(id=3, type=SourceType.CROP, level=0),
        SourcePit(id=4, type=SourceType.LUMBER, level=5),
        SourcePit(id=5, type=SourceType.CLAY, level=5),
        SourcePit(id=6, type=SourceType.CLAY, level=6),
        SourcePit(id=7, type=SourceType.IRON, level=5),
        SourcePit(id=8, type=SourceType.CROP, level=3),
        SourcePit(id=9, type=SourceType.CROP, level=5),
        SourcePit(id=10, type=SourceType.IRON, level=2),
        SourcePit(id=11, type=SourceType.IRON, level=5),
        SourcePit(id=12, type=SourceType.CROP, level=4),
        SourcePit(id=13, type=SourceType.CROP, level=5),
        SourcePit(id=14, type=SourceType.LUMBER, level=8),
        SourcePit(id=15, type=SourceType.CROP, level=3),
        SourcePit(id=16, type=SourceType.CLAY, level=7),
        SourcePit(id=17, type=SourceType.LUMBER, level=5),
        SourcePit(id=18, type=SourceType.CLAY, level=9)
    ]

    assert result == expected


def test_scan_village_center(dorf2_html):

    # When
    result = scan_village_center(dorf2_html)

    # Then
    expected = [
        Building(id=20, type=BuildingType.WAREHOUSE, level=7),
        Building(id=21, type=BuildingType.GRANARY, level=11),
        Building(id=26, type=BuildingType.MAIN_BUILDING, level=3),
        Building(id=39, type=BuildingType.RALLY_POINT, level=1)
    ]

    assert result == expected


def test_scan_village_name(dorf1_html):

    # When
    result = scan_village_name(dorf1_html)

    # Then
    assert result == "New village"


def test_scan_stock_bar(dorf1_html):
    # When
    result = scan_stock_bar(dorf1_html)

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
    # When
    result = scan_production(dorf1_html)

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
    identity = VillageIdentity(id=50287, name="New village", coordinate_x=2, coordinate_y=147)

    # When
    result = scan_village(identity, dorf1_html, dorf2_html)

    # Then
    expected = Village(
        id=50287,
        name="New village",
        tribe=result.tribe,
        lumber=5636,
        clay=5475,
        iron=5844,
        crop=14284,
        free_crop=1503,
        warehouse_capacity=6300,
        granary_capacity=14400,
        lumber_hourly_production=920,
        clay_hourly_production=1040,
        iron_hourly_production=690,
        crop_hourly_production=1504,
        free_crop_hourly_production=1503,
        source_pits=result.source_pits,
        buildings=result.buildings,
        building_queue=result.building_queue
    )
    assert result == expected


def test_scan_building_queue(dorf1_html):
    # When
    result = scan_building_queue(dorf1_html)

    # Then
    expected = [
        BuildingJob(building_id=0, target_level=2, time_remaining=98),
        BuildingJob(building_id=0, target_level=3, time_remaining=628)
    ]
    assert result == expected


def test_scan_account_info(dorf1_html):
    # When
    result = scan_account_info(dorf1_html)

    # Then
    expected = Account(
        server_speed=5.0,
        when_beginners_protection_expires=42778
    )
    assert result == expected


def test_identity_tribe(dorf2_html):
    # When
    result = identity_tribe(dorf2_html)

    # Then
    assert result == Tribe.ROMANS


def test_scan_hero_info(hero_attributes_html, inventory_html):
    # When
    result = scan_hero_info(hero_attributes_html, inventory_html)

    # Then
    expected = HeroInfo(
        health=90,
        experience=16594,
        adventures=83,
        is_available=True,
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
    html = HtmlUtils.load("hero_attributes_with_points.html")
    # When
    result = scan_hero_info(html, inventory_html)

    # Then
    assert result.points_available == 4


def test_scan_hero_info_without_attribute_points(hero_attributes_html, inventory_html):
    # Ensure existing fixture doesn't report attribute points
    result = scan_hero_info(hero_attributes_html, inventory_html)
    assert result.points_available == 0

def test_scan_hero_without_adventures():
    # Given
    html = """
           <a id="button6977c92fb7cdd" class="layoutButton buttonFramed withIcon round adventure green    "
              href="/hero/adventures">
               <svg viewBox="0 0 19.75 20" class="adventure"></svg>
           </a>
    """
    tag = BeautifulSoup(html, "html.parser")

    # When
    result = _parse_adventure_number(tag)

    # Then
    assert result == 0

def test_scan_hero_with_adventures():
    # Given
    html = """
           <a id="button6977c92fb7cdd" class="layoutButton buttonFramed withIcon round adventure green    "
              href="/hero/adventures">
               <div class="content">5</div>
           </a>
    """
    tag = BeautifulSoup(html, "html.parser")

    # When
    result = _parse_adventure_number(tag)

    # Then
    assert result == 5