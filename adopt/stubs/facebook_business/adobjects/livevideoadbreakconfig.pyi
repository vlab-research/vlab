from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class LiveVideoAdBreakConfig(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        default_ad_break_duration: str
        failure_reason_polling_interval: str
        first_break_eligible_secs: str
        guide_url: str
        is_eligible_to_onboard: str
        is_enabled: str
        onboarding_url: str
        preparing_duration: str
        time_between_ad_breaks_secs: str
        viewer_count_threshold: str
