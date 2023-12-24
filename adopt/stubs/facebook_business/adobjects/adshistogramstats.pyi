from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdsHistogramStats(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        field_1d_click: str
        field_1d_ev: str
        field_1d_view: str
        field_28d_click: str
        field_28d_view: str
        field_7d_click: str
        field_7d_view: str
        action_brand: str
        action_canvas_component_id: str
        action_canvas_component_name: str
        action_carousel_card_id: str
        action_carousel_card_name: str
        action_category: str
        action_converted_product_id: str
        action_destination: str
        action_device: str
        action_event_channel: str
        action_link_click_destination: str
        action_location_code: str
        action_reaction: str
        action_target_id: str
        action_type: str
        action_video_asset_id: str
        action_video_sound: str
        action_video_type: str
        dda: str
        inline: str
        interactive_component_sticker_id: str
        interactive_component_sticker_response: str
        skan_click: str
        skan_view: str
        value: str
