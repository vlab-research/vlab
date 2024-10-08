from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class LiveVideo(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_break_config: str
        ad_break_failure_reason: str
        broadcast_start_time: str
        copyright: str
        creation_time: str
        dash_ingest_url: str
        dash_preview_url: str
        description: str
        embed_html: str
        field_from: str
        id: str
        ingest_streams: str
        is_manual_mode: str
        is_reference_only: str
        live_views: str
        overlay_url: str
        permalink_url: str
        planned_start_time: str
        recommended_encoder_settings: str
        seconds_left: str
        secure_stream_url: str
        status: str
        stream_url: str
        targeting: str
        title: str
        total_views: str
        video: str
    class Projection:
        cubemap: str
        equirectangular: str
        half_equirectangular: str
    class SpatialAudioFormat:
        ambix_4: str
    class Status:
        live_now: str
        scheduled_canceled: str
        scheduled_live: str
        scheduled_unpublished: str
        unpublished: str
    class StereoscopicMode:
        left_right: str
        mono: str
        top_bottom: str
    class StreamType:
        ambient: str
        regular: str
    class BroadcastStatus:
        live: str
        live_stopped: str
        processing: str
        scheduled_canceled: str
        scheduled_expired: str
        scheduled_live: str
        scheduled_unpublished: str
        unpublished: str
        vod: str
    class Source:
        owner: str
        target: str
    class LiveCommentModerationSetting:
        value_default: str
        discussion: str
        followed: str
        follower: str
        no_hyperlink: str
        protected_mode: str
        restricted: str
        slow: str
        supporter: str
        tagged: str
    class PersistentStreamKeyStatus:
        disable: str
        enable: str
        regenerate: str
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_blocked_users(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_comments(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_crosspost_share_d_pages(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_crossposted_broadcasts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_errors(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_input_stream(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_polls(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_poll(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_reactions(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
