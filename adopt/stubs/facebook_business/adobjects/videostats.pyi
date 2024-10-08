from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class VideoStats(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        aggregate: str
        error: str
        metadata: str
        time_series: str
        totals: str
        x_axis_breakdown: str
