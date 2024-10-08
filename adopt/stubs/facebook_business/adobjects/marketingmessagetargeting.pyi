from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class MarketingMessageTargeting(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        automation_type: str
        delay_send_time_second: str
        delay_send_time_unit: str
        subscriber_lists: str
        targeting_rules: str
