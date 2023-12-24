from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAssetFeedSpecAssetCustomizationRule(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        body_label: str
        call_to_action_label: str
        call_to_action_type_label: str
        caption_label: str
        carousel_label: str
        customization_spec: str
        description_label: str
        image_label: str
        is_default: str
        link_url_label: str
        priority: str
        title_label: str
        video_label: str
