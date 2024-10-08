from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class MerchantReport(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        add_to_cart: str
        brand: str
        catalog_segment_id: str
        catalog_segment_purchase_value: str
        category: str
        date: str
        latest_date: str
        link_clicks: str
        merchant_currency: str
        page_id: str
        product_id: str
        product_quantity: str
        product_total_value: str
        purchase: str
        purchase_value: str
