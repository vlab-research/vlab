from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAssetFeedSpecVideo(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        adlabels: str
        caption_ids: str
        thumbnail_hash: str
        thumbnail_url: str
        url_tags: str
        video_id: str
