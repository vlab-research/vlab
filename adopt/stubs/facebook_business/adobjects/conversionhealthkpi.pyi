from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ConversionHealthKPI(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        health_indicator: str
        impacted_browsers_match_rate: str
        impacted_browsers_match_rate_mom_trend: str
        impacted_browsers_traffic_share: str
        impacted_browsers_traffic_share_mom_trend: str
        match_rate: str
        match_rate_mom_trend: str
        match_rate_vertical_benchmark: str
        match_rate_vs_benchmark_mom_trend: str
