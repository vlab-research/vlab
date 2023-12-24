from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ShadowIGMediaProductTags(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        image_url: str
        is_checkout: str
        merchant_id: str
        name: str
        price_string: str
        product_id: str
        review_status: str
        stripped_price_string: str
        stripped_sale_price_string: str
        x: str
        y: str
