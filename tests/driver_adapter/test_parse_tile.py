import pytest

from src.core.model.model import TileVillage, TileOasisFree, TileOasisOccupied
from src.driver_adapter.driver import Driver


class TestParseTile:
    """Tests for Driver._parse_tile static method."""

    def test_parse_tile_occupied_village(self) -> None:
        """Test parsing an occupied village with full player data."""
        tile_data = {
            "position": {"x": 99, "y": 109},
            "uid": 1787,
            "aid": 26,
            "did": 34158,
            "title": "{k.dt} 01 {k.volk} {a.v6}",
            "text": "</span></span>&#x202c;<br />{k.spieler} AnOos<br />{k.einwohner} 1112<br />{k.allianz} G.G<br />",
        }

        result = Driver._parse_tile(tile_data)

        assert isinstance(result, TileVillage)
        assert result.x == 99
        assert result.y == 109
        assert result.village_id == 34158
        assert result.user_id == 1787
        assert result.alliance_id == 26
        assert result.player_name == "AnOos"
        assert result.population == 1112
        assert result.alliance_name == "G.G"

    def test_parse_tile_free_oasis(self) -> None:
        """Test parsing a free (unoccupied) oasis tile."""
        tile_data = {
            "position": {"x": 175, "y": 59},
            "did": -1,
            "title": "{k.fo}",
            "text": '&#x202d;<span class="coordinates coordinatesWrapper"><span class="coordinateX">(&#x202d;175&#x202c;</span><span class="coordinatePipe">|</span><span class="coordinateY">&#x202d;59&#x202c;)</span></span>&#x202c;<br />{a:r1} {a.r1} 25%<br />{k.animals}<br /><div class="inlineIcon tooltipUnit" title=""><i class="unit u35"></i><span class="value ">1</span></div><br /><div class="inlineIcon tooltipUnit" title=""><i class="unit u36"></i><span class="value ">6</span></div>',
        }

        result = Driver._parse_tile(tile_data)

        assert isinstance(result, TileOasisFree)
        assert result.x == 175
        assert result.y == 59
        assert "{a.r1}" in result.bonus_resources
        assert result.animals == {"Rat": 1, "Spider": 6}  # Translated animal names

    def test_parse_tile_occupied_oasis(self) -> None:
        """Test parsing an occupied oasis tile."""
        tile_data = {
            "position": {"x": 176, "y": 58},
            "title": "{k.vt} {k.f3}",
            "text": '&#x202d;<span class="coordinates coordinatesWrapper"><span class="coordinateX">(&#x202d;176&#x202c;</span><span class="coordinatePipe">|</span><span class="coordinateY">&#x202d;58&#x202c;)</span></span>&#x202c;',
        }

        result = Driver._parse_tile(tile_data)

        assert isinstance(result, TileOasisOccupied)
        assert result.x == 176
        assert result.y == 58
        assert result.field_type == "4-4-4-6"  # f3 translated

    @pytest.mark.parametrize(
        "field_type_code,expected_field_type",
        [
            ("f1", "3-3-3-9"),
            ("f3", "4-4-4-6"),
            ("f10", "3-5-4-6"),
            ("f12", "5-4-3-6"),
            ("f6", "1-1-1-15"),
        ],
    )
    def test_parse_tile_occupied_oasis_field_types(
        self, field_type_code: str, expected_field_type: str
    ) -> None:
        """Test parsing occupied oases with different field types."""
        tile_data = {
            "position": {"x": 100, "y": 100},
            "title": f"{{k.vt}} {{k.{field_type_code}}}",
            "text": "...",
        }

        result = Driver._parse_tile(tile_data)

        assert isinstance(result, TileOasisOccupied)
        assert result.field_type == expected_field_type

    def test_parse_tile_decorative_forest_returns_none(self) -> None:
        """Test parsing decorative forest element returns None."""
        tile_data = {
            "position": {"x": 177, "y": 62},
            "title": "Forest",
            "text": '&#x202d;<span class="coordinates coordinatesWrapper"><span class="coordinateX">(&#x202d;177&#x202c;</span><span class="coordinatePipe">|</span><span class="coordinateY">&#x202d;62&#x202c;)</span></span>&#x202c;',
        }

        result = Driver._parse_tile(tile_data)

        assert result is None

    def test_parse_tile_decorative_lake_returns_none(self) -> None:
        """Test parsing decorative lake element returns None."""
        tile_data = {
            "position": {"x": 185, "y": 62},
            "title": "Lake",
            "text": '&#x202d;<span class="coordinates coordinatesWrapper"><span class="coordinateX">(&#x202d;185&#x202c;</span><span class="coordinatePipe">|</span><span class="coordinateY">&#x202d;62&#x202c;)</span></span>&#x202c;',
        }

        result = Driver._parse_tile(tile_data)

        assert result is None

    def test_parse_tile_village_extracts_tribe(self) -> None:
        """Test that tribe information is correctly extracted from title."""
        tile_data = {
            "position": {"x": 50, "y": 50},
            "uid": 100,
            "did": 200,
            "aid": 25,
            "title": "{k.dt} Village {k.volk} Romans",
            "text": "{k.spieler} Player1<br />{k.einwohner} 500<br />",
        }

        result = Driver._parse_tile(tile_data)

        assert isinstance(result, TileVillage)
        assert result.tribe == "Romans"

    def test_parse_tile_village_without_alliance(self) -> None:
        """Test parsing a village without alliance."""
        tile_data = {
            "position": {"x": 60, "y": 60},
            "uid": 150,
            "did": 250,
            "aid": None,
            "title": "{k.dt} Village",
            "text": "{k.spieler} SoloPlayer<br />{k.einwohner} 300<br />",
        }

        result = Driver._parse_tile(tile_data)

        assert isinstance(result, TileVillage)
        assert result.player_name == "SoloPlayer"
        assert result.population == 300
        assert result.alliance_name == ""
        assert result.alliance_id is None

    def test_parse_tile_decorative_element_returns_none(self) -> None:
        """Test that decorative elements (like {k.vt} without field type) are ignored."""
        tile_data = {
            "position": {"x": 103, "y": 114},
            "title": "{k.vt}",
            "text": '&#x202d;<span class="coordinates coordinatesWrapper">...</span>&#x202c;',
        }

        result = Driver._parse_tile(tile_data)

        assert result is None

    def test_parse_tile_empty_title_returns_none(self) -> None:
        """Test parsing a tile with empty title returns None (decorative element)."""
        tile_data = {
            "position": {"x": 70, "y": 70},
            "title": "",
            "text": "...",
        }

        result = Driver._parse_tile(tile_data)

        assert result is None

    def test_parse_tile_invalid_population_returns_zero(self) -> None:
        """Test that invalid population data defaults to 0."""
        tile_data = {
            "position": {"x": 80, "y": 80},
            "uid": 200,
            "did": 300,
            "aid": 40,
            "title": "{k.dt} Village",
            "text": "{k.spieler} Player<br />{k.einwohner} invalid<br />",
        }

        result = Driver._parse_tile(tile_data)

        assert isinstance(result, TileVillage)
        assert result.population == 0

    def test_parse_tile_missing_coordinates_defaults_to_zero(self) -> None:
        """Test that missing coordinates default to 0."""
        tile_data = {
            "position": {},
            "uid": 100,
            "did": 200,
            "aid": 50,
            "title": "{k.dt} Village",
            "text": "{k.spieler} Player<br />",
        }

        result = Driver._parse_tile(tile_data)

        assert isinstance(result, TileVillage)
        assert result.x == 0
        assert result.y == 0

    @pytest.mark.parametrize(
        "unit_code,expected_name",
        [
            ("u35", "Rat"),
            ("u36", "Spider"),
            ("u37", "Snake"),
            ("u38", "Bat"),
            ("u39", "Wild Boar"),
            ("u40", "Wolf"),
            ("u41", "Bear"),
            ("u42", "Crocodile"),
            ("u43", "Tiger"),
            ("u44", "Elephant"),
        ],
    )
    def test_parse_tile_free_oasis_animal_types(
        self, unit_code: str, expected_name: str
    ) -> None:
        """Test parsing free oases with different animal types."""
        tile_data = {
            "position": {"x": 100, "y": 100},
            "did": -1,
            "title": "{k.fo}",
            "text": f'{{k.animals}}<br /><div class="inlineIcon tooltipUnit" title=""><i class="unit {unit_code}"></i><span class="value ">5</span></div>',
        }

        result = Driver._parse_tile(tile_data)

        assert isinstance(result, TileOasisFree)
        assert result.animals == {expected_name: 5}

