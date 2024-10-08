from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ProductItemShipping(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        shipping_country: str
        shipping_price_currency: str
        shipping_price_value: str
        shipping_region: str
        shipping_service: str
