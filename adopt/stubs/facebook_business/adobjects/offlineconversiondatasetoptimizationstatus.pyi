from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class OfflineConversionDataSetOptimizationStatus(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        event: str
        last_changed_time: str
        last_detected_time: str
        status: str
