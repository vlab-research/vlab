from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdsPixelRealTimeEventLogResult(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        data_json: str
        dedup_data: str
        device_type: str
        domain_control_rule_rejection: str
        event: str
        event_detection_method: str
        in_iframe: str
        matched_rule_conditions: str
        resolved_link: str
        source_rule_condition: str
        timestamp: str
        trace_id: str
        url: str
