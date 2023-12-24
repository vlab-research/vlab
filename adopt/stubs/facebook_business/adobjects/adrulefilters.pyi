from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdRuleFilters(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        field: str
        operator: str
        value: str
    class Operator:
        all: str
        any: str
        contain: str
        equal: str
        greater_than: str
        value_in: str
        in_range: str
        less_than: str
        none: str
        not_contain: str
        not_equal: str
        not_in: str
        not_in_range: str
