from bs4 import BeautifulSoup

from src.scan_adapter.scanner_adapter import Scanner
from tests.scanner_adapter.html_utils import HtmlUtils


def test_daily_quest_indicator_present():
    # Given
    html = """
    <div id="navigation">
        <a class="dailyQuests" href="#" accesskey="7" onclick="Travian.React.openDailyQuestsDialog(); return false;">
            <div class="indicator">!</div>
        </a>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scanner = Scanner()

    # When
    nav = soup.select_one('#navigation')
    indicator = scanner.is_daily_quest_indicator(nav)

    # Then
    assert indicator is True


def test_daily_quest_indicator_absent_in_hero_attributes():
    # Given
    html = HtmlUtils.load("hero_attributes.html")
    soup = BeautifulSoup(html, "html.parser")
    nav = soup.select_one('#navigation')
    scanner = Scanner()

    # When
    indicator = scanner.is_daily_quest_indicator(nav)

    # Then
    assert indicator is False
