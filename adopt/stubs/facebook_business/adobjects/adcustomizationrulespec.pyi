from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCustomizationRuleSpec(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        caption: str
        customization_spec: str
        description: str
        image_hash: str
        link: str
        message: str
        name: str
        priority: str
        template_url_spec: str
        video_id: str
