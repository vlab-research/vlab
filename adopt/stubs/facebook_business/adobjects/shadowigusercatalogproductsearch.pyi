from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ShadowIGUserCatalogProductSearch(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        image_url: str
        is_checkout_flow: str
        merchant_id: str
        product_id: str
        product_name: str
        product_variants: str
        retailer_id: str
        review_status: str
