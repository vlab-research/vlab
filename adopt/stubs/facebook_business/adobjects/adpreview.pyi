from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.helpers.adpreviewmixin import AdPreviewMixin as AdPreviewMixin

class AdPreview(AdPreviewMixin, AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        body: str
        transformation_spec: str
    class AdFormat:
        audience_network_instream_video: str
        audience_network_instream_video_mobile: str
        audience_network_outstream_video: str
        audience_network_rewarded_video: str
        biz_disco_feed_mobile: str
        desktop_feed_standard: str
        facebook_profile_feed_desktop: str
        facebook_profile_feed_mobile: str
        facebook_profile_reels_mobile: str
        facebook_reels_banner: str
        facebook_reels_banner_desktop: str
        facebook_reels_mobile: str
        facebook_reels_postloop: str
        facebook_reels_sticker: str
        facebook_story_mobile: str
        facebook_story_sticker_mobile: str
        instagram_explore_contextual: str
        instagram_explore_grid_home: str
        instagram_explore_immersive: str
        instagram_feed_web: str
        instagram_feed_web_m_site: str
        instagram_lead_gen_multi_submit_ads: str
        instagram_profile_feed: str
        instagram_profile_reels: str
        instagram_reels: str
        instagram_reels_overlay: str
        instagram_search_chain: str
        instagram_search_grid: str
        instagram_standard: str
        instagram_story: str
        instagram_story_effect_tray: str
        instagram_story_web: str
        instagram_story_web_m_site: str
        instant_article_recirculation_ad: str
        instant_article_standard: str
        instream_banner_desktop: str
        instream_banner_fullscreen_mobile: str
        instream_banner_immersive_mobile: str
        instream_banner_mobile: str
        instream_video_desktop: str
        instream_video_fullscreen_mobile: str
        instream_video_image: str
        instream_video_immersive_mobile: str
        instream_video_mobile: str
        job_browser_desktop: str
        job_browser_mobile: str
        marketplace_mobile: str
        messenger_mobile_inbox_media: str
        messenger_mobile_story_media: str
        mobile_banner: str
        mobile_feed_basic: str
        mobile_feed_standard: str
        mobile_fullwidth: str
        mobile_interstitial: str
        mobile_medium_rectangle: str
        mobile_native: str
        right_column_standard: str
        suggested_video_desktop: str
        suggested_video_fullscreen_mobile: str
        suggested_video_immersive_mobile: str
        suggested_video_mobile: str
        watch_feed_home: str
        watch_feed_mobile: str
    class CreativeFeature:
        product_metadata_automation: str
        profile_card: str
        standard_enhancements_catalog: str
    class RenderType:
        fallback: str
    @classmethod
    def get_endpoint(cls): ...
