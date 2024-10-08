from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeFeaturesSpec(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        adapt_to_placement: str
        ads_with_benefits: str
        advantage_plus_creative: str
        app_highlights: str
        audio: str
        carousel_to_video: str
        catalog_feed_tag: str
        customize_product_recommendation: str
        cv_transformation: str
        description_automation: str
        dha_optimization: str
        feed_caption_optimization: str
        ig_glados_feed: str
        image_auto_crop: str
        image_background_gen: str
        image_brightness_and_contrast: str
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
        site_extensions: str
        standard_enhancements: str
        standard_enhancements_catalog: str
        text_generation: str
        text_optimizations: str
        video_auto_crop: str
        video_filtering: str
        video_highlight: str
