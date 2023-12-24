from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdRuleExecutionOptions(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        field: str
        operator: str
        value: str
    class Operator:
        equal: str
        value_in: str
