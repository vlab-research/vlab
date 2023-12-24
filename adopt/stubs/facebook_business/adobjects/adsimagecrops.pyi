from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdsImageCrops(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        field_100x100: str
        field_100x72: str
        field_191x100: str
        field_400x150: str
        field_400x500: str
        field_600x360: str
        field_90x160: str
