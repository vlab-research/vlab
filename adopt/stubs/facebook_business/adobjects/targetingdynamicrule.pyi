from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class TargetingDynamicRule(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        field_action_type: str
        ad_group_id: str
        campaign_group_id: str
        campaign_id: str
        impression_count: str
        page_id: str
        post: str
        retention_seconds: str
