from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class AdCampaignLearningStageInfo(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        attribution_windows: str = ...
        conversions: str = ...
        last_sig_edit_ts: str = ...
        status: str = ...
