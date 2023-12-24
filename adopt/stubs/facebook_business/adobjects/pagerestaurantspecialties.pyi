from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class PageRestaurantSpecialties(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        breakfast: str
        coffee: str
        dinner: str
        drinks: str
        lunch: str
