from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdsPixelEventSuggestionRule(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        field_7d_volume: str
        dismissed: str
        end_time: str
        event_type: str
        rank: str
        rule: str
        sample_urls: str
        start_time: str
