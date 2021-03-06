from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker
from typing import Any, Optional

class BusinessImage(AbstractCrudObject):
    def __init__(self, fbid: Optional[Any] = ..., parent_id: Optional[Any] = ..., api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        business: str = ...
        creation_time: str = ...
        hash: str = ...
        height: str = ...
        id: str = ...
        media_library_url: str = ...
        name: str = ...
        url: str = ...
        url_128: str = ...
        width: str = ...
        ad_placements_validation_only: str = ...
        bytes: str = ...
        creative_folder_id: str = ...
        validation_ad_placements: str = ...
    class ValidationAdPlacements:
        audience_network_instream_video: str = ...
        audience_network_instream_video_mobile: str = ...
        audience_network_rewarded_video: str = ...
        desktop_feed_standard: str = ...
        facebook_story_mobile: str = ...
        instagram_standard: str = ...
        instagram_story: str = ...
        instant_article_standard: str = ...
        instream_video_desktop: str = ...
        instream_video_image: str = ...
        instream_video_mobile: str = ...
        messenger_mobile_inbox_media: str = ...
        messenger_mobile_story_media: str = ...
        mobile_feed_standard: str = ...
        mobile_fullwidth: str = ...
        mobile_interstitial: str = ...
        mobile_medium_rectangle: str = ...
        mobile_native: str = ...
        right_column_standard: str = ...
        suggested_video_mobile: str = ...
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id: Any, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def api_delete(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def api_get(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_ad_placement_validation_results(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def delete_creative_asset_tags(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_creative_asset_tags(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def create_creative_asset_tag(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_insights(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., is_async: bool = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
