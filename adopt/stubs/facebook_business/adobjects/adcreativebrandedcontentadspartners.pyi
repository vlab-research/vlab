from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeBrandedContentAdsPartners(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        fb_page_id: str
        identity_type: str
        ig_asset_id: str
        ig_user_id: str
