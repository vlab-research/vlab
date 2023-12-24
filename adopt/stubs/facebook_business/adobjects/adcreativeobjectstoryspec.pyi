from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeObjectStorySpec(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        instagram_actor_id: str
        link_data: str
        page_id: str
        photo_data: str
        template_data: str
        text_data: str
        video_data: str
