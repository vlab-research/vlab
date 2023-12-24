from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class MinimumBudget(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        currency: str
        min_daily_budget_high_freq: str
        min_daily_budget_imp: str
        min_daily_budget_low_freq: str
        min_daily_budget_video_views: str
    @classmethod
    def get_endpoint(cls): ...
