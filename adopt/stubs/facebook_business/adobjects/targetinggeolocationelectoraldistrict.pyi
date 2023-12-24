from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class TargetingGeoLocationElectoralDistrict(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        country: str
        deprecation_code: str
        electoral_district: str
        key: str
        name: str
