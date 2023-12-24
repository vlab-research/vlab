from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AudiencePermissionForActions(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        can_edit: str
        can_see_insight: str
        can_share: str
        subtype_supports_lookalike: str
        supports_recipient_lookalike: str
