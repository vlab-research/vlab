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
        enable_advantage_plus_creative: str
        enable_autoflow: str
        endpoint_pinged: str
        error: str
        facebook_notification_sent: str
        message_sent: str
        not_changed: str
        paused: str
        unpaused: str
