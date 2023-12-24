from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class TargetingGeoLocationPlace(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        country: str
        distance_unit: str
        key: str
        latitude: str
        longitude: str
        name: str
        primary_city_id: str
        radius: str
        region_id: str
