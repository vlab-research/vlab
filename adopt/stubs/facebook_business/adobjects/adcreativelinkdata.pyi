from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class AdCreativeLinkData(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        additional_image_index: str = ...
        app_link_spec: str = ...
        attachment_style: str = ...
        branded_content_shared_to_sponsor_status: str = ...
        branded_content_sponsor_page_id: str = ...
        call_to_action: str = ...
        caption: str = ...
        child_attachments: str = ...
        collection_thumbnails: str = ...
        customization_rules_spec: str = ...
        description: str = ...
        event_id: str = ...
        force_single_link: str = ...
        format_option: str = ...
        image_crops: str = ...
        image_hash: str = ...
        image_layer_specs: str = ...
        image_overlay_spec: str = ...
        link: str = ...
        message: str = ...
        multi_share_end_card: str = ...
        multi_share_optimized: str = ...
        name: str = ...
        offer_id: str = ...
        page_welcome_message: str = ...
        picture: str = ...
        post_click_configuration: str = ...
        preferred_image_tags: str = ...
        retailer_item_ids: str = ...
        show_multiple_images: str = ...
        static_fallback_spec: str = ...
        use_flexible_image_aspect_ratio: str = ...
    class AttachmentStyle:
        value_default: str = ...
        link: str = ...
    class FormatOption:
        carousel_images_multi_items: str = ...
        carousel_images_single_item: str = ...
        carousel_slideshows: str = ...
        single_image: str = ...
