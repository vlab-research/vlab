from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ProductItemInsights(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_click_count: str
        ad_impression_count: str
        add_to_cart_count: str
        purchase_count: str
        view_content_count: str
