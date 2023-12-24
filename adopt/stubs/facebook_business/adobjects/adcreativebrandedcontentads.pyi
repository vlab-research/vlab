from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeBrandedContentAds(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_format: str
        creator_ad_permission_type: str
        instagram_boost_post_access_token: str
        is_mca_internal: str
        partners: str
        ui_version: str
