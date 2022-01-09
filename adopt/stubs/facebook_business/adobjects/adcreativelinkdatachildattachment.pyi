from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class AdCreativeLinkDataChildAttachment(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        call_to_action: str = ...
        caption: str = ...
        description: str = ...
        image_crops: str = ...
        image_hash: str = ...
        link: str = ...
        name: str = ...
        picture: str = ...
        place_data: str = ...
        static_card: str = ...
        video_id: str = ...