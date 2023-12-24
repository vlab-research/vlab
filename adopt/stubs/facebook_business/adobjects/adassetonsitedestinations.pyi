from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAssetOnsiteDestinations(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        auto_optimization: str
        details_page_product_id: str
        shop_collection_product_set_id: str
        storefront_shop_id: str
