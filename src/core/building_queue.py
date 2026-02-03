"""BuildingQueue manages building construction slots for villages.

In Travian, Romans have a special ability to build in parallel:
- One building in the village center (buildings with IDs 19-40)
- One resource field outside the center (source pits with IDs 1-18)

Other tribes can only build one structure at a time (shared slot).
"""

from dataclasses import dataclass
from src.core.model.model import Tribe


@dataclass
class BuildingSlot:
    """Represents a building slot in the queue."""
    
    building_id: int | None = None
    target_level: int | None = None
    
    def is_occupied(self) -> bool:
        """Check if the slot is currently occupied."""
        return self.building_id is not None and self.target_level is not None
    
    def clear(self) -> None:
        """Clear the slot."""
        self.building_id = None
        self.target_level = None


class BuildingQueue:
    """Manages building construction queue for a village.
    
    Romans can build in parallel (center + resource field).
    Other tribes share a single building slot.
    """
    
    def __init__(self, tribe: Tribe) -> None:
        """Initialize building queue based on tribe.
        
        Args:
            tribe: The tribe of the village
        """
        self.tribe = tribe
        
        if tribe == Tribe.ROMANS:
            # Romans have two independent slots
            self._center_slot = BuildingSlot()
            self._resource_field_slot = BuildingSlot()
        else:
            # Other tribes share a single slot for both
            self._shared_slot = BuildingSlot()
    
    def can_build_in_center(self) -> bool:
        """Check if a building can be constructed in the village center.
        
        Returns:
            True if the center slot is available, False otherwise
        """
        if self.tribe == Tribe.ROMANS:
            return not self._center_slot.is_occupied()
        else:
            return not self._shared_slot.is_occupied()
    
    def can_build_resource_field(self) -> bool:
        """Check if a resource field can be constructed.
        
        Returns:
            True if the resource field slot is available, False otherwise
        """
        if self.tribe == Tribe.ROMANS:
            return not self._resource_field_slot.is_occupied()
        else:
            return not self._shared_slot.is_occupied()
    
    def occupy_center_slot(self, building_id: int, target_level: int) -> None:
        """Occupy the center building slot.
        
        Args:
            building_id: ID of the building being constructed
            target_level: Target level of the building
        """
        if self.tribe == Tribe.ROMANS:
            self._center_slot.building_id = building_id
            self._center_slot.target_level = target_level
        else:
            self._shared_slot.building_id = building_id
            self._shared_slot.target_level = target_level
    
    def occupy_resource_field_slot(self, building_id: int, target_level: int) -> None:
        """Occupy the resource field slot.
        
        Args:
            building_id: ID of the resource field being constructed
            target_level: Target level of the resource field
        """
        if self.tribe == Tribe.ROMANS:
            self._resource_field_slot.building_id = building_id
            self._resource_field_slot.target_level = target_level
        else:
            self._shared_slot.building_id = building_id
            self._shared_slot.target_level = target_level
    
    def release_center_slot(self) -> None:
        """Release the center building slot."""
        if self.tribe == Tribe.ROMANS:
            self._center_slot.clear()
        else:
            self._shared_slot.clear()
    
    def release_resource_field_slot(self) -> None:
        """Release the resource field slot."""
        if self.tribe == Tribe.ROMANS:
            self._resource_field_slot.clear()
        else:
            self._shared_slot.clear()
    
    def is_building_in_center(self) -> bool:
        """Check if currently building in the center.
        
        Returns:
            True if center slot is occupied, False otherwise
        """
        if self.tribe == Tribe.ROMANS:
            return self._center_slot.is_occupied()
        else:
            # For non-Romans, check if shared slot is occupied
            # (we can't distinguish between center and resource field)
            return self._shared_slot.is_occupied()
    
    def is_building_resource_field(self) -> bool:
        """Check if currently building a resource field.
        
        Returns:
            True if resource field slot is occupied, False otherwise
        """
        if self.tribe == Tribe.ROMANS:
            return self._resource_field_slot.is_occupied()
        else:
            # For non-Romans, shared slot could be either
            return self._shared_slot.is_occupied()
    
    def is_empty(self) -> bool:
        """Check if the building queue is completely empty.
        
        Returns:
            True if no buildings are being constructed, False otherwise
        """
        if self.tribe == Tribe.ROMANS:
            return not self._center_slot.is_occupied() and not self._resource_field_slot.is_occupied()
        else:
            return not self._shared_slot.is_occupied()
    
    def get_occupied_slots(self) -> list[BuildingSlot]:
        """Get list of currently occupied building slots.
        
        Returns:
            List of occupied BuildingSlot objects
        """
        occupied = []
        
        if self.tribe == Tribe.ROMANS:
            if self._center_slot.is_occupied():
                occupied.append(self._center_slot)
            if self._resource_field_slot.is_occupied():
                occupied.append(self._resource_field_slot)
        else:
            if self._shared_slot.is_occupied():
                occupied.append(self._shared_slot)
        
        return occupied
