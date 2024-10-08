from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class InsightsValue(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        campaign_id: str
        end_time: str
        engagement_source: str
        message_type: str
        messaging_channel: str
        recurring_notifications_entry_point: str
        recurring_notifications_frequency: str
        recurring_notifications_topic: str
        start_time: str
        value: str
