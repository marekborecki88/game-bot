from unittest import TestCase

from src.core.model.Village import VillageIdentity
from src.scan_adapter.scanner import Scanner


# TODO: This test demand upgrade to scan multiple villages
def test_scan_village_list():
    scanner = Scanner()
    html = """
           <div class="villageList ">
               
               <div class="dropContainer" data-sortid="village37498" data-sortlevel="0">
                   <div class="listEntry village active" data-did="37498" data-sortid="village37498">
                       <a href="#" class="active">
                           <div class="iconAndNameWrapper"><span class="incomingTroops" data-id="37498"
                                                                 data-load-tooltip="incomingTroops"
                                                                 data-load-tooltip-data="{&quot;villageIds&quot;:[37498]}"><svg
                                   viewBox="0 0 20 19.06" class="attack"></svg></span><span
                                   class="name" data-did="37498">Sodoma</span></div>
                       </a>
                       <span class="coordinatesGrid">&#x202D;<span
                           class="coordinates coordinatesWrapper coordinatesAligned coordinatesltr"><span
                           class="coordinateX">(&#x202D;85&#x202C;</span><span class="coordinatePipe">|</span><span
                           class="coordinateY">&#x202D;−&#x202D;81&#x202C;&#x202C;)</span></span>&#x202C;
                       </span>
                   </div>
               </div>
           </div>
        """

    # When
    result = scanner.scan_village_list(html)

    # Then
    assert result == [
        VillageIdentity(id=37498, name="Sodoma", coordinate_x=85, coordinate_y=-81)
    ]


def test_scan_village_source():
    assert False

