from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class Stories(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        creation_time: str
        media_id: str
        media_type: str
        post_id: str
        status: str
        url: str
    class Status:
        archived: str
        published: str
