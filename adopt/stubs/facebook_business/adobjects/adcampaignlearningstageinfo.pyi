from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCampaignLearningStageInfo(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        attribution_windows: str
        conversions: str
        last_sig_edit_ts: str
        status: str
