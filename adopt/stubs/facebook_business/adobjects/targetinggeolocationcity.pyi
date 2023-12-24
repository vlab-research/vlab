from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class TargetingGeoLocationCity(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        country: str
        distance_unit: str
        key: str
        name: str
        radius: str
        region: str
        region_id: str
