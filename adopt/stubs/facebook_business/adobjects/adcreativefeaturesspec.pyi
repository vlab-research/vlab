from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeFeaturesSpec(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        advantage_plus_creative: str
        audio: str
        carousel_to_video: str
        cv_transformation: str
        description_automation: str
        dha_optimization: str
        ig_glados_feed: str
        image_auto_crop: str
        image_background_gen: str
        image_enhancement: str
        image_templates: str
        image_touchups: str
        image_uncrop: str
        inline_comment: str
        media_liquidity_animated_image: str
        media_order: str
        media_type_automation: str
        product_extensions: str
        product_metadata_automation: str
        product_tags: str
        profile_card: str
        standard_enhancements: str
        standard_enhancements_catalog: str
        text_generation: str
        text_optimizations: str
        video_auto_crop: str
        video_highlight: str
