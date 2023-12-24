from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class Profile(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        can_post: str
        id: str
        link: str
        name: str
        pic: str
        pic_crop: str
        pic_large: str
        pic_small: str
        pic_square: str
        profile_type: str
        username: str
    class ProfileType:
        application: str
        event: str
        group: str
        page: str
        user: str
    class Type:
        angry: str
        care: str
        fire: str
        haha: str
        hundred: str
        like: str
        love: str
        none: str
        pride: str
        sad: str
        thankful: str
        wow: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_picture(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
