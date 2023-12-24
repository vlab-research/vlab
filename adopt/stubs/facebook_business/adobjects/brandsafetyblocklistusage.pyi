from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class BrandSafetyBlockListUsage(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        current_usage: str
        new_usage: str
        platform: str
        position: str
        threshold: str
