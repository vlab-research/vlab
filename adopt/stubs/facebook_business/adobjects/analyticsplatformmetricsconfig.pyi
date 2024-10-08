from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AnalyticsPlatformMetricsConfig(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        has_a2u: str
        has_api_calls: str
        has_app_invites: str
        has_fb_login: str
        has_game_requests: str
        has_payments: str
        has_referrals: str
        has_stories: str
        has_structured_requests: str
