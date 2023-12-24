from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CustomAudienceSession(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        end_time: str
        num_invalid_entries: str
        num_matched: str
        num_received: str
        progress: str
        session_id: str
        stage: str
        start_time: str
