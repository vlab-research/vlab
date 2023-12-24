from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAssetFeedAdditionalData(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        automated_product_tags: str
        brand_page_id: str
        is_click_to_message: str
        multi_share_end_card: str
        page_welcome_message: str
