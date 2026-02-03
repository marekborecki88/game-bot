import math

from src.core.model.model import Resources, BuildingCost


# This code is translated and adapted from external JS Travian calculator:

class TimeT3:
    def __init__(self, a, k=1.16, b=None):
        self.a = a
        self.k = k
        if b is None:
            self.b = 1875 * k
        else:
            self.b = b

    def value_at(self, lvl):
        return self.a * math.pow(self.k, lvl - 1) - self.b

class TimeT5:
    mul = []
    def __init__(self, b=0, e=0):
        self.b = b
        self.e = e

    def value_at(self, lvl):
        return self.b * self.mul[lvl - 1] + self.e

class TimeT5a(TimeT5):
    mul = [1, 4.5, 15, 60, 120, 240, 360, 720, 1080, 1620, 2160, 2700, 3240, 3960, 4500, 5400, 7200, 9000, 10800, 14400]
    def __init__(self, b):
        super().__init__(b, 0)

class TimeT5b(TimeT5):
    mul = [3, 22.5, 48, 90, 210, 480, 720, 990, 1200, 1380, 1680, 1980, 2340, 2640, 3060, 3420, 3960, 4680, 5400, 6120]
    def __init__(self, b, e=0):
        super().__init__(b, e)

class TimeT5c(TimeT5):
    mul = [8, 25, 55, 140, 240]
    def __init__(self, e=0):
        super().__init__(60, e * 60)

class TimeT5w(TimeT5):
    mul = [12,16,20,24,28,32,36,40,44,46,46,47,48,48,49,50,51,51,52,53,54,55,57,58,59,60,62,63,64,66,67,69,70,72,74,75,77,79,81,83,85,87,89,91,93,96,98,100,103,105,107,110,113,115,118,121,123,126,129,132,135,138,141,144,147,150,154,157,160,164,167,171,174,178,181,185,189,193,196,200,204,208,212,216,220,225,229,233,237,242,246,251,255,260,264,269,274,278,288,576]
    def __init__(self):
        super().__init__(300, 0)

BUILDINGS_DATA = [
    {"gid": 1, "name": "Woodcutter", "cost": [40, 100, 50, 60], "k": 1.67, "time": TimeT3(1780/3, 1.6, 1000/3)},
    {"gid": 2, "name": "Clay Pit", "cost": [80, 40, 80, 50], "k": 1.67, "time": TimeT3(1660/3, 1.6, 1000/3)},
    {"gid": 3, "name": "Iron Mine", "cost": [100, 80, 30, 60], "k": 1.67, "time": TimeT3(2350/3, 1.6, 1000/3)},
    {"gid": 4, "name": "Cropland", "cost": [70, 90, 70, 20], "k": 1.67, "time": TimeT3(1450/3, 1.6, 1000/3)},
    {"gid": 5, "name": "Sawmill", "cost": [520, 380, 290, 90], "k": 1.80, "time": TimeT3(5400, 1.5, 2400)},
    {"gid": 6, "name": "Brickyard", "cost": [440, 480, 320, 50], "k": 1.80, "time": TimeT3(5240, 1.5, 2400)},
    {"gid": 7, "name": "Iron Foundry", "cost": [200, 450, 510, 120], "k": 1.80, "time": TimeT3(6480, 1.5, 2400)},
    {"gid": 8, "name": "Grain Mill", "cost": [500, 440, 380, 1240], "k": 1.80, "time": TimeT3(4240, 1.5, 2400)},
    {"gid": 9, "name": "Bakery", "cost": [1200, 1480, 870, 1600], "k": 1.80, "time": TimeT3(6080, 1.5, 2400)},
    {"gid": 10, "name": "Warehouse", "cost": [130, 160, 90, 40], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 11, "name": "Granary", "cost": [80, 100, 70, 20], "k": 1.28, "time": TimeT3(3475)},
    {"gid": 12, "name": "Blacksmith", "cost": [170, 200, 380, 130], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 13, "name": "Armoury", "cost": [130, 210, 410, 130], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 14, "name": "Tournament Square", "cost": [1750, 2250, 1530, 240], "k": 1.28, "time": TimeT3(5375)},
    {"gid": 15, "name": "Main Building", "cost": [70, 40, 60, 20], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 16, "name": "Rally Point", "cost": [110, 160, 90, 70], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 17, "name": "Marketplace", "cost": [80, 70, 120, 70], "k": 1.28, "time": TimeT3(3675)},
    {"gid": 18, "name": "Embassy", "cost": [180, 130, 150, 80], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 19, "name": "Barracks", "cost": [210, 140, 260, 120], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 20, "name": "Stable", "cost": [260, 140, 220, 100], "k": 1.28, "time": TimeT3(4075)},
    {"gid": 21, "name": "Workshop", "cost": [460, 510, 600, 320], "k": 1.28, "time": TimeT3(4875)},
    {"gid": 22, "name": "Academy", "cost": [220, 160, 90, 40], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 23, "name": "Cranny", "cost": [40, 50, 30, 10], "k": 1.28, "time": TimeT3(2625)},
    {"gid": 24, "name": "Town Hall", "cost": [1250, 1110, 1260, 600], "k": 1.28, "time": TimeT3(14375)},
    {"gid": 25, "name": "Residence", "cost": [580, 460, 350, 180], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 26, "name": "Palace", "cost": [550, 800, 750, 250], "k": 1.28, "time": TimeT3(6875)},
    {"gid": 27, "name": "Treasury", "cost": [2880, 2740, 2580, 990], "k": 1.26, "time": TimeT3(9875)},
    {"gid": 28, "name": "Trade Office", "cost": [1400, 1330, 1200, 400], "k": 1.28, "time": TimeT3(4875)},
    {"gid": 29, "name": "Great Barracks", "cost": [630, 420, 780, 360], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 30, "name": "Great Stable", "cost": [780, 420, 660, 300], "k": 1.28, "time": TimeT3(4075)},
    {"gid": 31, "name": "City Wall", "cost": [70, 90, 170, 70], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 32, "name": "Earth Wall", "cost": [120, 200, 0, 80], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 33, "name": "Palisade", "cost": [160, 100, 80, 60], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 34, "name": "Stonemason", "cost": [155, 130, 125, 70], "k": 1.28, "time": TimeT3(5950, 2)},
    {"gid": 35, "name": "Brewery", "cost": [1460, 930, 1250, 1740], "k": 1.40, "time": TimeT3(11750, 2)},
    {"gid": 36, "name": "Trapper", "cost": [100, 100, 100, 100], "k": 1.28, "time": TimeT3(2000, 0)},
    {"gid": 37, "name": "Hero's Mansion", "cost": [700, 670, 700, 240], "k": 1.33, "time": TimeT3(2300, 0)},
    {"gid": 38, "name": "Great Warehouse", "cost": [650, 800, 450, 200], "k": 1.28, "time": TimeT3(10875)},
    {"gid": 39, "name": "Great Granary", "cost": [400, 500, 350, 100], "k": 1.28, "time": TimeT3(8875)},
    {"gid": 40, "name": "Wonder of the World", "cost": [66700, 69050, 72200, 13200], "k": 1.0275, "time": TimeT3(60857, 1.014, 42857)},
    {"gid": 41, "name": "Horse Drinking Trough", "cost": [780, 420, 660, 540], "k": 1.28, "time": TimeT3(5950, 2)},
    {"gid": 42, "name": "Stone Wall", "cost": [110, 160, 70, 60], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 43, "name": "Makeshift Wall", "cost": [50, 80, 40, 30], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 44, "name": "Command Center", "cost": [1600, 1250, 1050, 200], "k": 1.22, "time": TimeT3(3875)},
    {"gid": 45, "name": "Waterworks", "cost": [910, 945, 910, 340], "k": 1.31, "time": TimeT3(3875)},
    {"gid": 46, "name": "Hospital", "cost": [320, 280, 420, 360], "k": 1.28, "time": TimeT3(4875)},
    {"gid": 47, "name": "Defensive wall", "cost": [240, 110, 275, 100], "k": 1.28, "time": TimeT3(2800, 1.16, 0)},
    {"gid": 48, "name": "Sapartans hosptial", "cost": [160, 100, 80, 60], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 49, "name": "Harbor", "cost": [1440, 1370, 1290, 495], "k": 1.28, "time": TimeT3(3875)},
    {"gid": 50, "name": "Barricade", "cost": [110, 170, 70, 50], "k": 1.28, "time": TimeT3(3875)},
]

# T4 overrides
T4_OVERRIDES = {
    13: {"cost": [180, 250, 500, 160], "name": "Smithy"},
    23: {"time": TimeT3(2175, 1.16, 1875)},
    36: {"cost": [80, 120, 70, 90]},
}

# T5 overrides
T5_OVERRIDES = {
    1: {"time": TimeT5a(24)},
    2: {"time": TimeT5a(22)},
    3: {"time": TimeT5a(30)},
    4: {"time": TimeT5a(20), "cost": [75, 90, 85, 0]},
    5: {"time": TimeT5c()},
    6: {"time": TimeT5c()},
    7: {"time": TimeT5c()},
    8: {"time": TimeT5c()},
    9: {"time": TimeT5c(5)},
    10: {"time": TimeT5b(11.5), "cost": [140, 180, 100, 0], "k": 1.33},
    11: {"time": TimeT5b(11), "cost": [80, 100, 70, 20], "k": 1.33},
    13: {"time": TimeT5b(13.3), "cost": [180, 250, 500, 160]},
    14: {"time": TimeT5b(26.1, 300)},
    15: {"time": TimeT5b(10.8), "k": 1.33},
    16: {"time": TimeT5b(11.5), "k": 1.33},
    17: {"time": TimeT5b(11.2)},
    18: {"time": TimeT5b(11.8), "cost": [700, 670, 700, 240], "k": 1.33},
    19: {"time": TimeT5b(12), "k": 1.33},
    20: {"time": TimeT5b(13), "k": 1.33},
    21: {"time": TimeT5b(15.5, 600)},
    22: {"time": TimeT5b(11.7), "k": 1.33},
    23: {"time": TimeT5b(3.3)},
    24: {"time": TimeT5b(21.9, 600)},
    25: {"time": TimeT5b(14.6, 1300)},
    26: {"time": TimeT5b(16.7, 3600)},
    27: {"time": TimeT5b(22.9, 2000), "cost": [1440, 1370, 1290, 495]},
    28: {"time": TimeT5b(22.2, 300)},
    29: {"time": TimeT5b(16.3, 600)},
    30: {"time": TimeT5b(16.2, 600)},
    31: {"time": TimeT5b(11.4)},
    32: {"time": TimeT5b(11.4)},
    33: {"time": TimeT5b(11.4)},
    34: {"time": TimeT5b(11.6)},
    35: {"time": TimeT5b(25, 600), "k": 1.28},
    36: {"time": TimeT5b(11.3), "cost": [80, 120, 70, 90], "k": 1.33},
    38: {"time": TimeT5b(8, 300)},
    39: {"time": TimeT5b(7, 300)},
    40: {"time": TimeT5w()},
    41: {"time": TimeT5b(16.9, 600)},
    42: {"name": "Water Ditch", "cost": [740, 850, 960, 620], "k": 1.28, "time": TimeT5b(19, 300)},
    43: {"name": "Natarian wall", "cost": [120, 200, 0, 80], "k": 1.28, "time": TimeT5b(11.4)},
}

def round_mul(v, n):
    return round(v / n) * n

def get_mb_factor(mb_level):
    if mb_level == 0:
        return 5
    return math.pow(0.964, mb_level - 1)

class TravianCalculator:
    def __init__(self, version="4.4", speed=1):
        self.version = version
        self.speed = speed
        self.major_version = int(version.split('.')[0])

        self.buildings = {b["gid"]: b.copy() for b in BUILDINGS_DATA}

        if self.major_version == 4:
            for gid, overrides in T4_OVERRIDES.items():
                if gid in self.buildings:
                    self.buildings[gid].update(overrides)

        if self.major_version == 5:
            for gid, overrides in T5_OVERRIDES.items():
                if gid in self.buildings:
                    self.buildings[gid].update(overrides)

    def get_building_by_name(self, name):
        for b in self.buildings.values():
            if b["name"].lower() == name.lower():
                return b
        return None

    def calculate_cost(self, building_name_or_gid, level):
        if isinstance(building_name_or_gid, str):
            b = self.get_building_by_name(building_name_or_gid)
        else:
            b = self.buildings.get(building_name_or_gid)

        if not b:
            return None

        k = b["k"]
        base_cost = b["cost"]

        if level == 0:
            return [0, 0, 0, 0]

        cost = [round_mul(v * math.pow(k, level - 1), 5) for v in base_cost]

        # Especial handling for Wonder of the World in some versions
        if b["gid"] == 40:
            cost = [min(v, 1000000) for v in cost]

        return cost

    def calculate_time(self, building_name_or_gid, level, main_building_level=1):
        if isinstance(building_name_or_gid, str):
            b = self.get_building_by_name(building_name_or_gid)
        else:
            b = self.buildings.get(building_name_or_gid)

        if not b:
            return None

        if level == 0:
            return 0

        time_obj = b["time"]
        base_time = time_obj.value_at(level)

        mb_factor = get_mb_factor(main_building_level)

        # Main Building special rule: level 1 means mb_factor is 1.25 for itself?
        # JS: if ((this.gid == 15) && (lvl == 1)) mb = 1.25;
        if b["gid"] == 15 and level == 1:
            mb_factor = 1.25
        elif b["gid"] == 15:
            # JS: mb = MB_Time(this.gid == 15 ? lvl-1 : _st.mb);
            mb_factor = get_mb_factor(level - 1)

        time = base_time * mb_factor / self.speed

        # JS rounded time based on version 5
        # function RoundMul(v, n) { return Math.round(v / n) * n; }
        # TableHelper.cellTime = function(cell, v) { ... r = (v>=1800) ? (v>=7200?300:60) : (v>=600?30:5); ... }
        # I'll just return raw seconds or rounded to nearest second
        return max(0, round(time))

    def get_building_details(self, building_name_or_gid, level, main_building_level=1) -> "BuildingCost":
        cost = self.calculate_cost(building_name_or_gid, level)
        time = self.calculate_time(building_name_or_gid, level, main_building_level)

        if cost is None:
            return None

        return BuildingCost(
            target_level=level,
            resources=Resources(lumber=cost[0],
                                clay=cost[1],
                                iron=cost[2],
                                crop=cost[3]),
            total=sum(cost),
            time_seconds=time,
            time_formatted=self._format_time(time)
        )

    def _format_time(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

