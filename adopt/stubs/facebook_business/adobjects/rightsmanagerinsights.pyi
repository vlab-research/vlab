from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class RightsManagerInsights(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        error: str
        error_message: str
        metadata: str
        totals: str
        x_axis_breakdown: str
