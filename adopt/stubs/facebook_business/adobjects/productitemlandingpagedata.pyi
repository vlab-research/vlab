from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ProductItemLandingPageData(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        availability: str
    class Availability:
        available_for_order: str
        discontinued: str
        in_stock: str
        mark_as_sold: str
        out_of_stock: str
        pending: str
        preorder: str
