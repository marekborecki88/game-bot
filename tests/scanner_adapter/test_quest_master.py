from src.infrastructure.scan_adapter.scanner_adapter import Scanner
from tests.scanner_adapter.html_utils import HtmlUtils


def test_is_reward_available_with_reward():
    # Given
    html = HtmlUtils.load("quest_master_with_reward.html")
    scanner = Scanner(server_speed=1)

    # When
    available = scanner.is_reward_available(html)

    # Then
    assert available is True


def test_is_reward_not_available_without_reward():
    # Given
    html = HtmlUtils.load("quest_master_without_reward.html")
    scanner = Scanner(server_speed=1)

    # When
    available = scanner.is_reward_available(html)

    # Then
    assert available is False


# keep previous negative test to ensure hero_attributes page still returns False
def test_is_reward_not_available_on_hero_attributes():
    # Given
    html = HtmlUtils.load("hero_attributes.html")
    scanner = Scanner(server_speed=1)

    # When
    available = scanner.is_reward_available(html)

    # Then
    assert available is False
