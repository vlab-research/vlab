from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CatalogItemAppLinks(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        android: str
        ios: str
        ipad: str
        iphone: str
        web: str
        windows: str
        windows_phone: str
        windows_universal: str
