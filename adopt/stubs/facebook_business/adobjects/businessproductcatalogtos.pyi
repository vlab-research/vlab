from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class BusinessProductCatalogTOS(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        accepted: str
        content: str
