from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeFeatureCustomizations(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        background_color: str
        catalog_feed_tag_name: str
        font_name: str
        product_recommendation_type: str
        showcase_card_display: str
        text_style: str
        video_crop_style: str
