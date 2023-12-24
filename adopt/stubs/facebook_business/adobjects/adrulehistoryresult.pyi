from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdRuleHistoryResult(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        actions: str
        object_id: str
        object_type: str
    class ObjectType:
        ad: str
        adset: str
        campaign: str
