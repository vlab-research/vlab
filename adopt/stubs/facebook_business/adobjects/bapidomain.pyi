from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class BAPIDomain(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        domain: str
        in_cool_down_until: str
        is_eligible_for_vo: str
        is_in_cool_down: str
