from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdsPixelStatsResult(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        aggregation: str
        data: str
        start_time: str
    class Aggregation:
        browser_type: str
        custom_data_field: str
        device_os: str
        device_type: str
        event: str
        event_detection_method: str
        event_processing_results: str
        event_source: str
        event_total_counts: str
        event_value_count: str
        had_pii: str
        host: str
        match_keys: str
        pixel_fire: str
        url: str
        url_by_rule: str
    @classmethod
    def get_endpoint(cls): ...
