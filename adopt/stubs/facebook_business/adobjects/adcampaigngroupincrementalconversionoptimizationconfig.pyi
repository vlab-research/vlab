from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCampaignGroupIncrementalConversionOptimizationConfig(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        action_type: str
        ad_study_end_time: str
        ad_study_id: str
        ad_study_name: str
        ad_study_start_time: str
        cell_id: str
        cell_name: str
        holdout_size: str
        ico_type: str
        objectives: str
