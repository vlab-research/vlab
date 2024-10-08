from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AnalyticsSegment(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        custom_audience_ineligiblity_reasons: str
        description: str
        estimated_custom_audience_size: str
        event_info_rules: str
        event_rules: str
        filter_set: str
        has_demographic_rules: str
        id: str
        is_all_user: str
        is_eligible_for_push_campaign: str
        is_internal: str
        name: str
        percentile_rules: str
        time_last_seen: str
        time_last_updated: str
        user_property_rules: str
        web_param_rules: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
