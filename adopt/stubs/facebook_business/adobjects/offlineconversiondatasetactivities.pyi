from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class OfflineConversionDataSetActivities(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        actor_id: str
        actor_name: str
        adaccount_id: str
        adaccount_name: str
        event_time: str
        event_type: str
        extra_data: str
        object_id: str
        object_name: str
