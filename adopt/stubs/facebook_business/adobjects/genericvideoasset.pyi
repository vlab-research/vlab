from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class GenericVideoAsset(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        broadcast_id: str
        broadcast_planned_start_time: str
        can_viewer_edit: str
        copyright_monitoring_status: str
        created_time: str
        creator: str
        description: str
        download_hd_url: str
        download_sd_url: str
        embeddable: str
        expiration: str
        feed_type: str
        id: str
        is_crossposting_eligible: str
        is_crossposting_within_bm_eligible: str
        is_crossposting_within_bm_enabled: str
        is_episode: str
        is_featured: str
        is_live_premiere: str
        is_video_asset: str
        last_added_time: str
        latest_creator: str
        latest_owned_description: str
        latest_owned_title: str
        length: str
        live_status: str
        no_story: str
        owner_name: str
        owner_picture: str
        owner_post_state: str
        permalink_url: str
        picture: str
        posts_count: str
        posts_ids: str
        posts_status: str
        premiere_living_room_status: str
        published: str
        scheduled_publish_time: str
        secret: str
        secure_stream_url: str
        social_actions: str
        status: str
        stream_url: str
        thumbnail_while_encoding: str
        title: str
        views: str
