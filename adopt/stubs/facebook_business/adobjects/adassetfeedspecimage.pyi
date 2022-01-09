from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class AdAssetFeedSpecImage(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        adlabels: str = ...
        hash: str = ...
        image_crops: str = ...
        url: str = ...
        url_tags: str = ...