from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAccountCustomAudienceLimits(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        audience_update_quota_in_total: str
        audience_update_quota_left: str
        has_hit_audience_update_limit: str
        next_audience_update_available_time: str
        rate_limit_reset_time: str
