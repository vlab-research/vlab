from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeVideoData(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        additional_image_index: str
        branded_content_shared_to_sponsor_status: str
        branded_content_sponsor_page_id: str
        call_to_action: str
        collection_thumbnails: str
        customization_rules_spec: str
        image_hash: str
        image_url: str
        link_description: str
        message: str
        offer_id: str
        page_welcome_message: str
        post_click_configuration: str
        retailer_item_ids: str
        targeting: str
        title: str
        video_id: str
