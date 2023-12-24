from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class TrackingAndConversionWithDefaults(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        custom_conversion: str
        custom_tracking: str
        default_conversion: str
        default_tracking: str
