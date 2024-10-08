from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class ExpirablePost(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        admin_creator: str
        can_republish: str
        content_type: str
        creation_time: str
        expiration: str
        feed_audience_description: str
        feed_targeting: str
        id: str
        is_post_in_good_state: str
        message: str
        modified_time: str
        og_action_summary: str
        permalink_url: str
        place: str
        privacy_description: str
        scheduled_failure_notice: str
        scheduled_publish_time: str
        story_token: str
        thumbnail: str
        video_id: str
