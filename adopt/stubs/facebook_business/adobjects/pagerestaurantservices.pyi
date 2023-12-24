from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class PageRestaurantServices(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        catering: str
        delivery: str
        groups: str
        kids: str
        outdoor: str
        pickup: str
        reserve: str
        takeout: str
        waiter: str
        walkins: str
