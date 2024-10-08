from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdKpiShift(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_set: str
        cost_per_result_shift: str
        enough_effective_days: str
        result_indicator: str
        result_shift: str
        spend_shift: str
