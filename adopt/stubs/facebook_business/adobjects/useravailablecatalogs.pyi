from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class UserAvailableCatalogs(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        catalog_id: str
        catalog_name: str
        product_count: str
        shop_name: str
