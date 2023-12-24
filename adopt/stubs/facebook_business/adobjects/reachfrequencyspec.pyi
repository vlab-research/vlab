from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ReachFrequencySpec(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        countries: str
        default_creation_data: str
        global_io_max_campaign_duration: str
        max_campaign_duration: str
        max_days_to_finish: str
        max_pause_without_prediction_rerun: str
        min_campaign_duration: str
        min_reach_limits: str
