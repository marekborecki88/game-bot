import logging
import random
from typing import Iterable

from playwright.sync_api import Playwright, Locator

from src.config.config import DriverConfig
from src.core.bot import HERO_INVENTORY, CLOSE_CONTENT_BUTTON_SELECTOR, RESOURCE_TO_CLASS_MAP
from src.core.protocols.driver_protocol import DriverProtocol
from src.core.model.model import Resources, Tile, TileVillage, TileOasisFree, TileOasisOccupied, TileAbandonedValley

RESOURCE_TRANSFER_SUBMIT_SELECTOR = 'button.withText.green'

RESOURCE_TRANSFER_INPUT_SELECTOR = 'input[inputmode="numeric"]'

# Field type translations from game codes to resource distributions
FIELD_TYPE_TRANSLATIONS = {
    "f1": "3-3-3-9",
    "f2": "3-4-5-6",
    "f3": "4-4-4-6",
    "f4": "4-5-3-6",
    "f5": "5-3-4-6",
    "f6": "1-1-1-15",
    "f7": "4-4-3-7",
    "f8": "3-4-4-7",
    "f9": "4-3-4-7",
    "f10": "3-5-4-6",
    "f11": "4-3-5-6",
    "f12": "5-4-3-6",
    "f13": "0-0-0-18",
    "f99": "Natarian village",
}

# Oasis bonus translations
OASIS_BONUS_TRANSLATIONS = {
    "w1-2": "+25% lumber per hour",
    "w3": "+25% lumber and +25% crop per hour",
    "w4-5": "+25% clay per hour",
    "w6": "+25% clay and +25% crop per hour",
    "w7-8": "+25% iron per hour",
    "w9": "+25% iron and +25% crop per hour",
    "w10-11": "+25% crop per hour",
    "w12": "+50% crop per hour",
}

# Animal/troop unit translations for oases
ANIMAL_TRANSLATIONS = {
    "u35": "Rat",
    "u36": "Spider",
    "u37": "Snake",
    "u38": "Bat",
    "u39": "Wild Boar",
    "u40": "Wolf",
    "u41": "Bear",
    "u42": "Crocodile",
    "u43": "Tiger",
    "u44": "Elephant",
}

# Tile parsing markers
ABANDONED_MARKER = "{k.vt}"
FIELD_TYPE_MARKER = "{k.f"
FREE_OASIS_MARKER = "{k.fo}"
RESOURCE_BONUS_MARKER = "{a.r"
TRIBE_MARKER = "{k.volk}"
POPULATION_MARKER = "{k.einwohner}"
PLAYER_MARKER = "{k.spieler}"
ALLIANCE_MARKER = "{k.allianz}"
ANIMALS_MARKER = "{k.animals}"

logger = logging.getLogger(__name__)


class Driver(DriverProtocol):
    def __init__(self, playwright: Playwright, driver_config: DriverConfig):
        self.playwright = playwright
        self.config = driver_config
        self.browser = self.playwright.chromium.launch(headless=self.config.headless)
        self.page = self.browser.new_page()
        self.login()

    def login(self) -> None:
        self.page.goto(self.config.server_url)

        self.page.wait_for_load_state('networkidle')

        self.page.fill('input[name="name"]', self.config.user_login)
        self.page.fill('input[name="password"]', self.config.user_password)

        # move mouse to random position within login button and click
        login_button: Locator = self.page.locator('button[type="submit"]').first
        box = login_button.bounding_box()
        if box:
            x = box["x"] + random.uniform(0, box["width"])
            y = box["y"] + random.uniform(0, box["height"])
            self.page.mouse.move(x, y)
            self.page.mouse.click(x, y)

        #wait
        self.sleep(5)

        self.page.wait_for_load_state('networkidle')

        logger.info("Successfully logged in.")

    def stop(self) -> None:
        try:
            self.browser.close()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

    def navigate(self, path: str) -> None:
        """Navigate to a path on the configured server and wait for load.

        This is the single public navigation method used throughout the codebase.
        """
        url = f"{self.config.server_url}{path}"

        # Log where we're navigating to for easier tracing
        logger.debug(f"Navigating to: {url}")

        self.page.goto(url)
        self.page.wait_for_load_state('networkidle')

    def get_html(self, path: str) -> str:
        self.navigate(path)
        return self.page.content()

    def navigate_to_village(self, village_id: int) -> None:
        self.navigate(f"/dorf1.php?newdid={village_id}")

    def refresh(self) -> None:
        self.page.reload()

    def get_village_inner_html(self, village_id: int) -> tuple[str, str]:
        self.navigate_to_village(village_id)
        dorf1: str = self.get_html("/dorf1.php")
        dorf2: str = self.get_html("/dorf2.php")

        return dorf1, dorf2

    # --- Public primitives only ---
    def click(self, selector: str) -> bool:
        """Click first element matching selector if visible; return True on click."""
        try:
            locator = self.page.locator(selector).first
            if locator.count() and locator.is_visible():
                try:
                    locator.click()
                    return True
                except Exception as e:
                    logger.debug(f"Click found element but click failed for selector: {selector}. Error: {e}")
                    return True
        except Exception:
            pass
        return False

    def click_first(self, selectors: Iterable[str]) -> bool:
        """Try selectors in order and click the first visible element found."""
        for sel in selectors:
            try:
                locator = self.page.locator(sel).first
                if locator.count() and locator.is_visible():
                    try:
                        locator.click()
                        return True
                    except Exception:
                        logger.debug(f"Element found but click failed for selector: {sel}")
                        return True
            except Exception:
                continue
        return False

    def click_all(self, selectors: Iterable[str]) -> int:
        """Click all visible elements matching provided selectors."""
        clicks = 0
        for sel in selectors:
            try:
                loc = self.page.locator(sel)
                count = loc.count()
                for i in range(count):
                    el = loc.nth(i)
                    try:
                        if el.is_visible():
                            el.click()
                            clicks += 1
                    except Exception:
                        logger.debug(f"Click failed for element matched by selector: {sel}")
                        continue
            except Exception:
                continue
        return clicks

    def wait_for_load_state(self, timeout: int = 3000) -> None:
        """Wait for page to settle; swallow non-fatal errors."""
        try:
            self.page.wait_for_load_state('networkidle', timeout=timeout)
        except Exception:
            pass

    def current_url(self) -> str:
        return self.page.url


    def transfer_resources_from_hero(self, support: Resources):
        self.navigate(HERO_INVENTORY)

        for item_id, amount in vars(support).items():
            if amount > 0:
                self.transfer_resource(amount, item_id)

        logger.info(f"Transferred {support} from hero inventory.")
        self.click(CLOSE_CONTENT_BUTTON_SELECTOR)


    def transfer_resource(self, amount, item_id: str):
        cls = RESOURCE_TO_CLASS_MAP.get(item_id)
        selector = f"item {cls} none"
        logger.debug(f"Try to click {selector}")
        self._wait_for_selector_and_click_by_class(selector)
        # wait for input to appear
        self.wait_for_selector(RESOURCE_TRANSFER_INPUT_SELECTOR, timeout=2000)
        # self._fill_input('input[inputmode="numeric"]', str(amount))
        self.page.fill(RESOURCE_TRANSFER_INPUT_SELECTOR, str(amount))
        self.click(RESOURCE_TRANSFER_SUBMIT_SELECTOR)

    def _wait_for_selector_and_click_by_class(self, class_name: str) -> bool:
        self.wait_for_selector(class_name)
        return self.page.evaluate(
            """
                (cls) => {
                    const el = document.getElementsByClassName(cls)[0];
                    if (el) {
                        el.click();
                        return true;
                    }
                    return false;
                }
            """,
            class_name,
        )

    def wait_for_selector(self, selector: str, timeout: int = 3000) -> bool:
        try:
            self.page.wait_for_selector(selector.replace(" ", "."), timeout=timeout)
            return True
        except Exception:
            return False

    def click_nth(self, selector: str, index: int) -> bool:
        try:
            locs = self.page.locator(selector)
            if locs.count() > index:
                el = locs.nth(index)
                if el.is_visible():
                    try:
                        el.click()
                        return True
                    except Exception:
                        logger.debug(f"click_nth failed for selector={selector} index={index}")
                        return False
        except Exception:
            pass
        return False

    def wait_for_selector_and_click(self, selector: str, timeout: int = 3000) -> None:
        self.wait_for_selector(selector, timeout=timeout)
        self.click(selector)

    def catch_full_classes_by_selector(self, selector: str) -> str:
        return self.page.locator(selector).first.get_attribute("class") or ""

    def sleep(self, seconds: int) -> None:
        self.page.wait_for_timeout(seconds * 1000)

    def is_visible(self, selector: str) -> bool:
        try:
            locator = self.page.locator(selector).first
            return locator.count() > 0 and locator.is_visible()
        except Exception:
            return False

    def get_text_content(self, selector: str) -> str:
        try:
            locator = self.page.locator(selector).first
            if locator.count() > 0:
                return locator.text_content() or ""
        except Exception:
            pass
        return ""

    def press_key(self, param):
        try:
            self.page.keyboard.press(param)
        except Exception as e:
            logger.debug(f"press_key failed for param={param} with error: {e}")

    def select_option(self, param, param1):
        try:
            self.page.select_option(param, param1)
        except Exception as e:
            logger.debug(f"select_option failed for param={param} param1={param1} with error: {e}")

    def catch_response(self, package_name: str) -> dict[str, str]:
        with self.page.expect_response(lambda res: "position" in res.url) as response_info:
            response = response_info.value
            if response.status == 200:
                data = response.json()
                return data

        return {}

    def scan_map(self, coordinates: tuple[int, int]) -> list[Tile]:
        # Navigate to the map
        self.navigate(f"/karte.php?fullscreen=1&x={coordinates[0]}&y={coordinates[1]}&zoom=1")

        position = self.catch_response("position")
        tiles = position.get("tiles", [])

        map_tiles: list[Tile] = []
        for tile in tiles:
            parsed_tile = self._parse_tile(tile)
            if parsed_tile:
                map_tiles.append(parsed_tile)

        return map_tiles

    @staticmethod
    def _parse_tile(tile: dict) -> Tile | None:
        """
        Parse a single tile dictionary into appropriate Tile subclass.

        Args:
            tile: Dictionary containing tile data from the game API

        Returns:
            Tile object (TileVillage, TileOasisFree, TileOasisOccupied, or TileAbandonedValley) or None if parsing fails
        """
        title = tile.get("title", "")
        text = tile.get("text", "")
        x_coord = tile.get("position", {}).get("x", 0)
        y_coord = tile.get("position", {}).get("y", 0)

        if Driver._is_free_oasis(tile, title):
            return Driver._create_free_oasis(x_coord, y_coord, text)

        if Driver._is_occupied_oasis(tile, title):
            return Driver._create_occupied_oasis(x_coord, y_coord, title)

        if Driver._is_abandoned_valley(tile, title):
            return Driver._create_abandoned_valley(x_coord, y_coord, title)

        if Driver._is_occupied_village(tile):
            return Driver._create_occupied_village(tile, x_coord, y_coord, title, text)

        # Everything else (decorative elements like "Forest", "Lake") is ignored
        return None

    @staticmethod
    def _is_free_oasis(tile: dict, title: str) -> bool:
        """Check if tile represents a free oasis - has {k.fo} marker."""
        return FREE_OASIS_MARKER in title

    @staticmethod
    def _is_occupied_oasis(tile: dict, title: str) -> bool:
        """Check if tile represents an occupied oasis - has {k.vt} AND field type marker."""
        has_no_player = tile.get("uid") is None
        has_abandoned_marker = ABANDONED_MARKER in title
        has_field_type_marker = FIELD_TYPE_MARKER in title
        return has_no_player and has_abandoned_marker and has_field_type_marker

    @staticmethod
    def _is_abandoned_valley(tile: dict, title: str) -> bool:
        """Check if tile represents an abandoned valley - TODO: need to identify marker."""
        # TODO: Identify abandoned valley marker when we see it in real data
        return False

    @staticmethod
    def _is_occupied_village(tile: dict) -> bool:
        """Check if tile represents an occupied village - has player (uid)."""
        return tile.get("uid") is not None

    @staticmethod
    def _create_free_oasis(x: int, y: int, text: str) -> TileOasisFree:
        """Create TileOasisFree with resource bonus and animals."""
        bonus_resources = Driver._extract_resource_bonus(text)
        animals = Driver._extract_animals(text)
        return TileOasisFree(x=x, y=y, bonus_resources=bonus_resources, animals=animals)

    @staticmethod
    def _create_occupied_oasis(x: int, y: int, title: str) -> TileOasisOccupied:
        """Create TileOasisOccupied with translated field type."""
        field_type = Driver._extract_and_translate_field_type(title)
        return TileOasisOccupied(x=x, y=y, field_type=field_type)

    @staticmethod
    def _create_abandoned_valley(x: int, y: int, title: str) -> TileAbandonedValley:
        """Create TileAbandonedValley with translated field type."""
        field_type = Driver._extract_and_translate_field_type(title)
        return TileAbandonedValley(x=x, y=y, field_type=field_type)



    @staticmethod
    def _create_occupied_village(
        tile: dict, x: int, y: int, title: str, text: str
    ) -> TileVillage:
        """Create occupied TileVillage with all player data."""
        return TileVillage(
            x=x,
            y=y,
            village_id=tile.get("did"),
            user_id=tile.get("uid"),
            alliance_id=tile.get("aid"),
            tribe=Driver._extract_tribe(title),
            population=Driver._extract_population(text),
            player_name=Driver._extract_player_name(text),
            alliance_name=Driver._extract_alliance_name(text),
        )

    @staticmethod
    def _extract_and_translate_field_type(title: str) -> str:
        """Extract field type code from title and translate to human-readable format."""
        if FIELD_TYPE_MARKER not in title:
            return ""

        try:
            field_part = title.split(FIELD_TYPE_MARKER)[1].split("}")[0]
            field_code = f"f{field_part}"
            return FIELD_TYPE_TRANSLATIONS.get(field_code, field_code)
        except (IndexError, ValueError):
            return ""

    @staticmethod
    def _extract_resource_bonus(text: str) -> str:
        """Extract resource bonus from text (e.g., '{a.r1} 25%')."""
        if RESOURCE_BONUS_MARKER not in text:
            return ""

        try:
            # Extract the part like "{a.r1} 25%"
            bonus_part = text.split(RESOURCE_BONUS_MARKER)[1].split("<br")[0]
            return f"{{a.r{bonus_part}"
        except (IndexError, ValueError):
            return ""

    @staticmethod
    def _extract_animals(text: str) -> dict[str, int]:
        """Extract animals from text and translate to readable names (e.g., 'Spider': 6, 'Rat': 1)."""
        if ANIMALS_MARKER not in text:
            return {}

        animals = {}
        try:
            # Find all animal units in the text
            animal_section = text.split(ANIMALS_MARKER)[1]
            # Extract unit types and counts using simple parsing
            import re
            units = re.findall(r'unit u(\d+).*?value[^>]*>(\d+)', animal_section)
            for unit_id, count in units:
                unit_code = f"u{unit_id}"
                animal_name = ANIMAL_TRANSLATIONS.get(unit_code, unit_code)
                animals[animal_name] = int(count)
        except (IndexError, ValueError):
            pass

        return animals

    @staticmethod
    def _extract_tribe(title: str) -> str:
        """Extract tribe information from title."""
        if TRIBE_MARKER not in title:
            return ""
        return title.split(TRIBE_MARKER)[1].strip()

    @staticmethod
    def _extract_population(text: str) -> int:
        """Extract population from text."""
        if POPULATION_MARKER not in text:
            return 0

        try:
            population_part = text.split(POPULATION_MARKER)[1].split("<br")[0].strip()
            return int(population_part)
        except (IndexError, ValueError):
            return 0

    @staticmethod
    def _extract_player_name(text: str) -> str:
        """Extract player name from text."""
        if PLAYER_MARKER not in text:
            return ""
        return text.split(PLAYER_MARKER)[1].split("<br")[0].strip()

    @staticmethod
    def _extract_alliance_name(text: str) -> str:
        """Extract alliance name from text."""
        if ALLIANCE_MARKER not in text:
            return ""
        return text.split(ALLIANCE_MARKER)[1].split("<br")[0].strip()

    def send_merchant(self, origin_village_id: int, market_field_id: int, target_village_coordinates: tuple[int, int], resources: Resources):
        # go to the sender village
        self.navigate_to_village(origin_village_id)

        # open merchant send interface for the specific field
        self.navigate(f"/build.php?id={origin_village_id}&gid=17&market={market_field_id}&t=5")

        # fill in target coordinates
        self.page.fill('input[name="x"]', str(target_village_coordinates[0]))
        self.page.fill('input[name="y"]', str(target_village_coordinates[1]))

        # fill in resources <input inputmode="numeric" class="" autocomplete="off" tabindex="4" type="text" value="0" name="lumber">
        self.page.fill('input[name="lumber"]', str(resources.lumber))
        self.page.fill('input[name="clay"]', str(resources.clay))
        self.page.fill('input[name="iron"]', str(resources.iron))
        self.page.fill('input[name="crop"]', str(resources.crop))

        # catch duration <div class="duration">Duration:&nbsp;<span class="value">0:00:32</span></div>
        self.page.wait_for_selector('div.duration span.value')
        duration_text = self.page.locator('div.duration span.value').first.text_content() or ""
        logger.info(f"Calculated merchant travel duration: {duration_text}")

        # submit the form <div class="actionButtons"><button class="textButtonV2 buttonFramed send rectangle withText green" type="submit" title=""><div>Send resources</div></button></div>
        self.click('button[type="submit"].withText.green')






