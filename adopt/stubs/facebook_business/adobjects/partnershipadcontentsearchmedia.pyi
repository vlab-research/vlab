from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class PartnershipAdContentSearchMedia(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ig_media: str
        ig_media_has_product_tags: str
        is_ad_code_entry: str
