from .base import Algorithm
from .always_on import AlwaysOn
from .always_off import AlwaysOff
from .household import HouseholdLighting
from .street_lamp import StreetLamp
from .railway_lighting import RailwayLighting
from .corridor import CorridorLighting
from .shop import Shop
from .shop_window import ShopWindow
from .minute import Minute

ALGORITHM_CLASSES = (AlwaysOn, AlwaysOff, HouseholdLighting, StreetLamp,
                     RailwayLighting, CorridorLighting, Shop, ShopWindow, Minute)
ALGORITHMS = {cls.identifier: cls for cls in ALGORITHM_CLASSES}
ALGORITHM_LABELS = {key: cls.name() for key, cls in ALGORITHMS.items()}
