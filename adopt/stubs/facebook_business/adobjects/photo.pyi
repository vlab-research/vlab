from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker
from typing import Any, Optional

class Photo(AbstractCrudObject):
    def __init__(self, fbid: Optional[Any] = ..., parent_id: Optional[Any] = ..., api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        album: str = ...
        alt_text: str = ...
        alt_text_custom: str = ...
        backdated_time: str = ...
        backdated_time_granularity: str = ...
        can_backdate: str = ...
        can_delete: str = ...
        can_tag: str = ...
        created_time: str = ...
        event: str = ...
        field_from: str = ...
        height: str = ...
        icon: str = ...
        id: str = ...
        images: str = ...
        link: str = ...
        name: str = ...
        name_tags: str = ...
        page_story_id: str = ...
        picture: str = ...
        place: str = ...
        position: str = ...
        source: str = ...
        target: str = ...
        updated_time: str = ...
        webp_images: str = ...
        width: str = ...
    class BackdatedTimeGranularity:
        day: str = ...
        hour: str = ...
        min: str = ...
        month: str = ...
        none: str = ...
        year: str = ...
    class UnpublishedContentType:
        ads_post: str = ...
        draft: str = ...
        inline_created: str = ...
        published: str = ...
        reviewable_branded_content: str = ...
        scheduled: str = ...
        scheduled_recurring: str = ...
    class Type:
        profile: str = ...
        tagged: str = ...
        uploaded: str = ...
    def api_delete(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def api_get(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_comments(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def create_comment(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_insights(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., is_async: bool = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_likes(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def create_like(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_shared_posts(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_sponsor_tags(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...