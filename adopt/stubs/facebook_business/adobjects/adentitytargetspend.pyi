from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdEntityTargetSpend(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        amount: str
        has_error: str
        is_accurate: str
        is_prorated: str
        is_updating: str
