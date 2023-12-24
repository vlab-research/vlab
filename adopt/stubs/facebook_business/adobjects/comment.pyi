from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class Comment(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        admin_creator: str
        application: str
        attachment: str
        can_comment: str
        can_hide: str
        can_like: str
        can_remove: str
        can_reply_privately: str
        comment_count: str
        created_time: str
        field_from: str
        id: str
        is_hidden: str
        is_private: str
        like_count: str
        live_broadcast_timestamp: str
        message: str
        message_tags: str
        object: str
        parent: str
        permalink_url: str
        private_reply_conversation: str
        user_likes: str
    class CommentPrivacyValue:
        declined_by_admin_assistant: str
        default_privacy: str
        friends_and_post_owner: str
        friends_only: str
        graphql_multiple_value_hack_do_not_use: str
        owner_or_commenter: str
        pending_approval: str
        removed_by_admin_assistant: str
        side_conversation: str
        side_conversation_and_post_owner: str
        spotlight_tab: str
    class Filter:
        stream: str
        toplevel: str
    class LiveFilter:
        filter_low_quality: str
        no_filter: str
    class Order:
        chronological: str
        reverse_chronological: str
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_comments(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_comment(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_likes(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_likes(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_like(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_reactions(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
