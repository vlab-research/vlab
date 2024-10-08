from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdRuleHistory(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        evaluation_spec: str
        exception_code: str
        exception_message: str
        execution_spec: str
        is_manual: str
        results: str
        schedule_spec: str
        timestamp: str
    class Action:
        budget_not_redistributed: str
        changed_bid: str
        changed_budget: str
        email: str
        enable_advantage_campaign_budget: str
        enable_advantage_plus_creative: str
        enable_advantage_plus_placements: str
        enable_autoflow: str
        enable_gen_uncrop: str
        enable_music: str
        enable_semantic_based_audience_expansion: str
        enable_shops_ads: str
        endpoint_pinged: str
        error: str
        facebook_notification_sent: str
        message_sent: str
        not_changed: str
        paused: str
        unpaused: str
