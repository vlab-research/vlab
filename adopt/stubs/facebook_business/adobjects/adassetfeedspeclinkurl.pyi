from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAssetFeedSpecLinkURL(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        adlabels: str
        carousel_see_more_url: str
        deeplink_url: str
        display_url: str
        url_tags: str
        website_url: str
