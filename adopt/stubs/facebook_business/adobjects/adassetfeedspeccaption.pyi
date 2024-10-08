from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAssetFeedSpecCaption(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        adlabels: str
        text: str
        url_tags: str
