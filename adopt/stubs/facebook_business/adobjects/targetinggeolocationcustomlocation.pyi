from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class TargetingGeoLocationCustomLocation(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        address_string: str
        country: str
        country_group: str
        custom_type: str
        distance_unit: str
        key: str
        latitude: str
        longitude: str
        max_population: str
        min_population: str
        name: str
        primary_city_id: str
        radius: str
        region_id: str
