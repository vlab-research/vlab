from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeBrandedContentAds(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_format: str
        content_search_input: str
        creator_ad_permission_type: str
        facebook_boost_post_access_token: str
        instagram_boost_post_access_token: str
        is_mca_internal: str
        partners: str
        promoted_page_id: str
        ui_version: str
