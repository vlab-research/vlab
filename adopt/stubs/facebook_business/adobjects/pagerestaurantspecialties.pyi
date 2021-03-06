from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class PageRestaurantSpecialties(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        breakfast: str = ...
        coffee: str = ...
        dinner: str = ...
        drinks: str = ...
        lunch: str = ...
