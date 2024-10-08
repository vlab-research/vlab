from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ProfilePictureSource(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        bottom: str
        cache_key: str
        height: str
        is_silhouette: str
        left: str
        right: str
        top: str
        url: str
        width: str
    class Type:
        album: str
        small: str
        thumbnail: str
