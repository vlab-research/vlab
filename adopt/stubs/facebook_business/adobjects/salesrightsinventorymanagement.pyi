from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class SalesRightsInventoryManagement(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        available_impressions: str
        booked_impressions: str
        overbooked_impressions: str
        supported_countries: str
        total_impressions: str
        unavailable_impressions: str
        warning_messages: str
