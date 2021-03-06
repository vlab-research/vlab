from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class ProfilePictureSource(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        bottom: str = ...
        cache_key: str = ...
        height: str = ...
        is_silhouette: str = ...
        left: str = ...
        right: str = ...
        top: str = ...
        url: str = ...
        width: str = ...
    class Type:
        album: str = ...
        small: str = ...
        thumbnail: str = ...
