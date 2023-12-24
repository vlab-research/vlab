from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class Photo(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        album: str
        alt_text: str
        alt_text_custom: str
        backdated_time: str
        backdated_time_granularity: str
        can_backdate: str
        can_delete: str
        can_tag: str
        created_time: str
        event: str
        field_from: str
        height: str
        icon: str
        id: str
        images: str
        link: str
        name: str
        name_tags: str
        page_story_id: str
        picture: str
        place: str
        position: str
        source: str
        target: str
        updated_time: str
        webp_images: str
        width: str
    class BackdatedTimeGranularity:
        day: str
        hour: str
        min: str
        month: str
        none: str
        year: str
    class UnpublishedContentType:
        ads_post: str
        draft: str
        inline_created: str
        published: str
        reviewable_branded_content: str
        scheduled: str
        scheduled_recurring: str
    class Type:
        profile: str
        tagged: str
        uploaded: str
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_comments(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_comment(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_insights(self, fields: Incomplete | None = None, params: Incomplete | None = None, is_async: bool = False, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_likes(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_like(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_sponsor_tags(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
