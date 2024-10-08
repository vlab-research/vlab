from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class VideoGroup(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        created_time: str
        description: str
        disable_reason: str
        id: str
        ig_profile_ids: str
        is_disabled: str
        is_fb_video_group: str
        last_used_time: str
        length: str
        name: str
        page_id: str
        page_ids: str
        picture: str
        placements: str
        video_group_types: str
        videos: str
        views: str
