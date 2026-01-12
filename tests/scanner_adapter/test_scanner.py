import pytest
from pathlib import Path

from src.core.model.Village import VillageIdentity, SourcePit, SourceType
from src.scan_adapter.scanner import Scanner


@pytest.fixture
def html_content():
    test_dir = Path(__file__).parent
    html_file = test_dir / "dorf1.html"
    return html_file.read_text(encoding='utf-8')


def test_scan_village_list(html_content):
    # Given
    scanner = Scanner()

    # When
    result = scanner.scan_village_list(html_content)

    # Then
    assert len(result) == 3
    assert result[0] == VillageIdentity(id=50275, name="SODOMA", coordinate_x=1, coordinate_y=146)
    assert result[1] == VillageIdentity(id=50281, name="GOMORA", coordinate_x=2, coordinate_y=146)
    assert result[2] == VillageIdentity(id=50287, name="New village", coordinate_x=2, coordinate_y=147)


def test_scan_village_source(html_content):
    # Given
    scanner = Scanner()

    # When
    result = scanner.scan_village_source(html_content)

    # Then
    assert len(result) == 18
    # Check all 18 resource fields
    assert result[0] == SourcePit(id=1, type=SourceType.LUMBER, level=5)
    assert result[1] == SourcePit(id=2, type=SourceType.CROP, level=5)
    assert result[2] == SourcePit(id=3, type=SourceType.CROP, level=5)
    assert result[3] == SourcePit(id=4, type=SourceType.LUMBER, level=5)
    assert result[4] == SourcePit(id=5, type=SourceType.CLAY, level=5)
    assert result[5] == SourcePit(id=6, type=SourceType.CLAY, level=6)
    assert result[6] == SourcePit(id=7, type=SourceType.IRON, level=5)
    assert result[7] == SourcePit(id=8, type=SourceType.CROP, level=5)
    assert result[8] == SourcePit(id=9, type=SourceType.CROP, level=5)
    assert result[9] == SourcePit(id=10, type=SourceType.IRON, level=5)
    assert result[10] == SourcePit(id=11, type=SourceType.IRON, level=5)
    assert result[11] == SourcePit(id=12, type=SourceType.CROP, level=5)
    assert result[12] == SourcePit(id=13, type=SourceType.CROP, level=5)
    assert result[13] == SourcePit(id=14, type=SourceType.LUMBER, level=5)
    assert result[14] == SourcePit(id=15, type=SourceType.CROP, level=5)
    assert result[15] == SourcePit(id=16, type=SourceType.CLAY, level=5)
    assert result[16] == SourcePit(id=17, type=SourceType.LUMBER, level=5)
    assert result[17] == SourcePit(id=18, type=SourceType.CLAY, level=5)


