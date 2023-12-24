from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class VoipInfo(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        has_mobile_app: str
        has_permission: str
        is_callable: str
        is_callable_webrtc: str
        is_pushable: str
        reason_code: str
        reason_description: str
