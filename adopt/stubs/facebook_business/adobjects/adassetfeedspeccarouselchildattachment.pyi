from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAssetFeedSpecCarouselChildAttachment(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        body_label: str
        call_to_action_type_label: str
        caption_label: str
        description_label: str
        image_label: str
        link_url_label: str
        phone_data_ids_label: str
        static_card: str
        title_label: str
        video_label: str
