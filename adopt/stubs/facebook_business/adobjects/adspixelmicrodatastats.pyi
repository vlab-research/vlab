from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdsPixelMicrodataStats(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        allowed_domains: str
        errors_stats_for_time_ranges: str
        has_valid_events: str
        suggested_allowed_domains_count_max: str
        suggested_trusted_domains: str
