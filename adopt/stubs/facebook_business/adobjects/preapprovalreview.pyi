from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class PreapprovalReview(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        comp_type: str
        crow_component_id: str
        is_human_reviewed: str
        is_reviewed: str
        policy_info: str
