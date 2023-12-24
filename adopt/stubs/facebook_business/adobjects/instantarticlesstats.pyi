from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class InstantArticlesStats(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        error: str
        metadata: str
        metric: str
        totals: str
        x_axis_breakdown: str
