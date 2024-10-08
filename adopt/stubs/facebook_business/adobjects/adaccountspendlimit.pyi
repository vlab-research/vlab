from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAccountSpendLimit(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        amount_spent: str
        group_id: str
        limit_id: str
        limit_value: str
        time_created: str
        time_start: str
        time_stop: str
