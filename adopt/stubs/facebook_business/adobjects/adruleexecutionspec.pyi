from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdRuleExecutionSpec(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        execution_options: str
        execution_type: str
        id: str
    class ExecutionType:
        add_interest_relaxation: str
        add_questionnaire_interests: str
        audience_consolidation: str
        audience_consolidation_ask_first: str
        change_bid: str
        change_budget: str
        change_campaign_budget: str
        increase_radius: str
        notification: str
        pause: str
        ping_endpoint: str
        rebalance_budget: str
        rotate: str
        unpause: str
        update_creative: str
        update_lax_budget: str
        update_lax_duration: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
