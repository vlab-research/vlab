from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAssetFeedSpecImage(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        adlabels: str
        hash: str
        image_crops: str
        url: str
        url_tags: str
