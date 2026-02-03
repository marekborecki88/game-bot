"""Tests for BuildingQueue class that manages building jobs for villages."""

import pytest
from src.core.model.model import Tribe
from src.core.building_queue import BuildingQueue, BuildingSlot


def test_building_queue_initialization_for_romans():
    """Romans should have two slots: one for center and one for resource fields."""
    queue = BuildingQueue(tribe=Tribe.ROMANS)
    
    assert queue.tribe == Tribe.ROMANS
    assert queue.can_build_in_center() is True
    assert queue.can_build_resource_field() is True


def test_building_queue_initialization_for_non_romans():
    """Non-Roman tribes should have one slot that can build anywhere."""
    queue = BuildingQueue(tribe=Tribe.GAULS)
    
    assert queue.tribe == Tribe.GAULS
    assert queue.can_build_in_center() is True
    assert queue.can_build_resource_field() is True


def test_romans_can_build_center_and_resource_field_parallel():
    """Romans should be able to build in center and resource field at the same time."""
    queue = BuildingQueue(tribe=Tribe.ROMANS)
    
    # Occupy center slot
    queue.occupy_center_slot(building_id=25, target_level=5)
    assert queue.can_build_in_center() is False
    assert queue.can_build_resource_field() is True
    
    # Occupy resource field slot
    queue.occupy_resource_field_slot(building_id=1, target_level=3)
    assert queue.can_build_in_center() is False
    assert queue.can_build_resource_field() is False


def test_romans_release_center_slot():
    """Romans should be able to release center slot."""
    queue = BuildingQueue(tribe=Tribe.ROMANS)
    
    queue.occupy_center_slot(building_id=25, target_level=5)
    assert queue.can_build_in_center() is False
    
    queue.release_center_slot()
    assert queue.can_build_in_center() is True


def test_romans_release_resource_field_slot():
    """Romans should be able to release resource field slot."""
    queue = BuildingQueue(tribe=Tribe.ROMANS)
    
    queue.occupy_resource_field_slot(building_id=1, target_level=3)
    assert queue.can_build_resource_field() is False
    
    queue.release_resource_field_slot()
    assert queue.can_build_resource_field() is True


def test_non_romans_share_single_slot():
    """Non-Roman tribes should share a single building slot."""
    queue = BuildingQueue(tribe=Tribe.GAULS)
    
    # Occupy the shared slot with center building
    queue.occupy_center_slot(building_id=25, target_level=5)
    assert queue.can_build_in_center() is False
    assert queue.can_build_resource_field() is False
    
    # Release it
    queue.release_center_slot()
    assert queue.can_build_in_center() is True
    assert queue.can_build_resource_field() is True


def test_non_romans_slot_with_resource_field():
    """Non-Roman tribes building resource field should occupy the shared slot."""
    queue = BuildingQueue(tribe=Tribe.TEUTONS)
    
    queue.occupy_resource_field_slot(building_id=2, target_level=4)
    assert queue.can_build_in_center() is False
    assert queue.can_build_resource_field() is False
    
    queue.release_resource_field_slot()
    assert queue.can_build_in_center() is True
    assert queue.can_build_resource_field() is True


def test_is_building_in_center_for_romans():
    """Check if Romans are building in center."""
    queue = BuildingQueue(tribe=Tribe.ROMANS)
    
    assert queue.is_building_in_center() is False
    queue.occupy_center_slot(building_id=25, target_level=5)
    assert queue.is_building_in_center() is True


def test_is_building_resource_field_for_romans():
    """Check if Romans are building in resource field."""
    queue = BuildingQueue(tribe=Tribe.ROMANS)
    
    assert queue.is_building_resource_field() is False
    queue.occupy_resource_field_slot(building_id=1, target_level=3)
    assert queue.is_building_resource_field() is True


def test_building_queue_is_empty_for_romans():
    """Check if building queue is completely empty for Romans."""
    queue = BuildingQueue(tribe=Tribe.ROMANS)
    
    assert queue.is_empty() is True
    
    queue.occupy_center_slot(building_id=25, target_level=5)
    assert queue.is_empty() is False
    
    queue.occupy_resource_field_slot(building_id=1, target_level=3)
    assert queue.is_empty() is False
    
    queue.release_center_slot()
    assert queue.is_empty() is False
    
    queue.release_resource_field_slot()
    assert queue.is_empty() is True


def test_building_queue_is_empty_for_non_romans():
    """Check if building queue is empty for non-Romans."""
    queue = BuildingQueue(tribe=Tribe.GAULS)
    
    assert queue.is_empty() is True
    
    queue.occupy_center_slot(building_id=25, target_level=5)
    assert queue.is_empty() is False
    
    queue.release_center_slot()
    assert queue.is_empty() is True


def test_building_slot_dataclass():
    """Test BuildingSlot dataclass."""
    slot = BuildingSlot(building_id=25, target_level=5)
    
    assert slot.building_id == 25
    assert slot.target_level == 5
    assert slot.is_occupied() is True
    
    empty_slot = BuildingSlot()
    assert empty_slot.is_occupied() is False


def test_romans_get_occupied_slots():
    """Romans should return information about occupied slots."""
    queue = BuildingQueue(tribe=Tribe.ROMANS)
    
    queue.occupy_center_slot(building_id=25, target_level=5)
    queue.occupy_resource_field_slot(building_id=1, target_level=3)
    
    slots = queue.get_occupied_slots()
    assert len(slots) == 2
    assert any(s.building_id == 25 and s.target_level == 5 for s in slots)
    assert any(s.building_id == 1 and s.target_level == 3 for s in slots)


def test_non_romans_get_occupied_slots():
    """Non-Romans should return information about the single occupied slot."""
    queue = BuildingQueue(tribe=Tribe.TEUTONS)
    
    queue.occupy_center_slot(building_id=25, target_level=5)
    
    slots = queue.get_occupied_slots()
    assert len(slots) == 1
    assert slots[0].building_id == 25
    assert slots[0].target_level == 5
