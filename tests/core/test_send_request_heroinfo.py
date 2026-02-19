import pytest

from src.domain.model.model import (
    HeroInfo,
    ReservationResponse,
    Resources, ReservationStatus,
)


@pytest.mark.parametrize(
    "hero_inventory, request_resources, expected_status, expected_provided",
    [
        # REJECTED: hero has only iron, request is for lumber and clay
        (
            {"iron": 100},
            Resources(lumber=10, clay=5, iron=0, crop=0),
            ReservationStatus.REJECTED,
            Resources(lumber=0, clay=0, iron=0, crop=0),
        ),
        # ACCEPTED: hero has all requested resources in sufficient quantity
        (
            {"lumber": 10, "iron": 10},
            Resources(lumber=10, clay=0, iron=5, crop=0),
            ReservationStatus.PARTIALLY_ACCEPTED,
            Resources(lumber=10, clay=0, iron=5, crop=0),
        ),
        # PARTIALLY_ACCEPTED: hero can provide only some of requested types
        (
            {"clay": 2},
            Resources(lumber=10, clay=5, iron=0, crop=0),
            ReservationStatus.PARTIALLY_ACCEPTED,
            Resources(lumber=0, clay=2, iron=0, crop=0),
        ),
        # No resources requested -> REJECTED (nothing to fulfill)
        (
            {"lumber": 10, "clay": 10, "iron": 10, "crop": 10},
            Resources(lumber=0, clay=0, iron=0, crop=0),
            ReservationStatus.REJECTED,
            Resources(lumber=0, clay=0, iron=0, crop=0),
        ),
    ],
)
def test_send_request_various_scenarios(
    hero_inventory: dict, request_resources: Resources, expected_status: ReservationStatus, expected_provided: Resources
) -> None:
    hero = HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory=hero_inventory)

    response = hero.send_request(request_resources)

    assert isinstance(response, ReservationResponse)
    assert response.status == expected_status
    assert response.provided_resources == expected_provided
