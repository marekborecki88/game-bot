import pytest
from pathlib import Path

from src.core.model.Village import VillageIdentity
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


def test_scan_village_source():
    assert False

