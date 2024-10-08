from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdsSignalDiagnosticIssue(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        data_source_id: str
        data_source_type: str
        diagnostic_type: str
        event_name: str
        traffic_anomaly_drop_percentage: str
        traffic_anomaly_drop_timestamp: str
