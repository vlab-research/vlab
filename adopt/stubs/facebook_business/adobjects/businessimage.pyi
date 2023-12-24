from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class BusinessImage(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        business: str
        creation_time: str
        hash: str
        height: str
        id: str
        media_library_url: str
        name: str
        url: str
        url_128: str
        width: str
        ad_placements_validation_only: str
        bytes: str
        creative_folder_id: str
        validation_ad_placements: str
    class ValidationAdPlacements:
        audience_network_instream_video: str
        audience_network_instream_video_mobile: str
        audience_network_rewarded_video: str
        desktop_feed_standard: str
        facebook_story_mobile: str
        facebook_story_sticker_mobile: str
        instagram_standard: str
        instagram_story: str
        instant_article_standard: str
        instream_banner_desktop: str
        instream_banner_mobile: str
        instream_video_desktop: str
        instream_video_image: str
        instream_video_mobile: str
        messenger_mobile_inbox_media: str
        messenger_mobile_story_media: str
        mobile_feed_standard: str
        mobile_fullwidth: str
        mobile_interstitial: str
        mobile_medium_rectangle: str
        mobile_native: str
        right_column_standard: str
        suggested_video_mobile: str
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
