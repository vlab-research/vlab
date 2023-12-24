from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAssetFeedSpecGroupRule(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        body_label: str
        caption_label: str
        description_label: str
        image_label: str
        link_url_label: str
        title_label: str
        video_label: str
