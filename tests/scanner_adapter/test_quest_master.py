from src.scan_adapter.scanner import is_reward_available
from tests.scanner_adapter.html_utils import HtmlUtils


def test_is_reward_available_with_reward():
    html = HtmlUtils.load("quest_master_with_reward.html")

    assert is_reward_available(html) is True


def test_is_reward_not_available_without_reward():
    html = HtmlUtils.load("quest_master_without_reward.html")

    assert is_reward_available(html) is False


# keep previous negative test to ensure hero_attributes page still returns False
def test_is_reward_not_available_on_hero_attributes():
    html = HtmlUtils.load("hero_attributes.html")

    assert is_reward_available(html) is False
