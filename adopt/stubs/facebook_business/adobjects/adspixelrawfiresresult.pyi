from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdsPixelRawFiresResult(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        data_json: str
        device_type: str
        event: str
        event_detection_method: str
        event_src: str
        placed_url: str
        timestamp: str
        user_pii_keys: str
