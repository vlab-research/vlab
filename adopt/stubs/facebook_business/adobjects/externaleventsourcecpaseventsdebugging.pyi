from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ExternalEventSourceCPASEventsDebugging(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        actual_event_time: str
        app_version: str
        content_url: str
        device_os: str
        diagnostic: str
        event_name: str
        event_time: str
        missing_ids: str
        severity: str
