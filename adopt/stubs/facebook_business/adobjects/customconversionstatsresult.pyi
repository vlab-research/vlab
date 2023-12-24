from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CustomConversionStatsResult(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        aggregation: str
        data: str
        timestamp: str
    class Aggregation:
        count: str
        device_type: str
        host: str
        pixel_fire: str
        unmatched_count: str
        unmatched_usd_amount: str
        url: str
        usd_amount: str
