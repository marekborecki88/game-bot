from pathlib import Path

import pytest

from src.core.model.Village import VillageIdentity, SourcePit, SourceType, Building, BuildingType
from src.scan_adapter.scanner import Scanner, scan_village_name, scan_stock_bar


@pytest.fixture
def dorf1_html():
    test_dir = Path(__file__).parent
    html_file = test_dir / "dorf1.html"
    return html_file.read_text(encoding='utf-8')


@pytest.fixture
def dorf2_html():
    test_dir = Path(__file__).parent
    html_file = test_dir / "dorf2.html"
    return html_file.read_text(encoding='utf-8')


def test_scan_village_list(dorf1_html):
    # Given
    scanner = Scanner()

    # When
    result = scanner.scan_village_list(dorf1_html)

    # Then
    expected = [
        VillageIdentity(id=50275, name="SODOMA", coordinate_x=1, coordinate_y=146),
        VillageIdentity(id=50281, name="GOMORA", coordinate_x=2, coordinate_y=146),
        VillageIdentity(id=50287, name="New village", coordinate_x=2, coordinate_y=147)
    ]
    assert result == expected


def test_scan_village_source(dorf1_html):
    # Given
    scanner = Scanner()

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
    # Given
    scanner = Scanner()

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
    # Given
    scanner = Scanner()

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

