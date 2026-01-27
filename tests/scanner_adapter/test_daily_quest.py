from bs4 import BeautifulSoup
from src.scan_adapter.scanner import is_daily_quest_indicator
from tests.scanner_adapter.html_utils import HtmlUtils


def test_daily_quest_indicator_present():
    html = """
    <div id="navigation">
        <a class="dailyQuests" href="#" accesskey="7" onclick="Travian.React.openDailyQuestsDialog(); return false;">
            <div class="indicator">!</div>
        </a>
    </div>
    """

    soup = BeautifulSoup(html, "html.parser")
    nav = soup.select_one('#navigation')

    assert is_daily_quest_indicator(nav) is True


def test_daily_quest_indicator_absent_in_hero_attributes():
    html = HtmlUtils.load("hero_attributes.html")
    soup = BeautifulSoup(html, "html.parser")
    nav = soup.select_one('#navigation')
    assert is_daily_quest_indicator(nav) is False
