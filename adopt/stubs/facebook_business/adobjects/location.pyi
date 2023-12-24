from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class Location(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        city: str
        city_id: str
        country: str
        country_code: str
        latitude: str
        located_in: str
        longitude: str
        name: str
        region: str
        region_id: str
        state: str
        street: str
        zip: str
