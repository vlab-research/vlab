from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCampaignDeliveryStats(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        bid_recommendation: str
        current_average_cost: str
        last_significant_edit_ts: str
        learning_stage_exit_info: str
        learning_stage_info: str
        unsupported_features: str
