from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AppEventConfig(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        breakdowns_config: str
        builtin_fields_config: str
        deprecated_events_config: str
        events_config: str
        id: str
        ios_purchase_validation_secret: str
        is_any_role_able_to_see_restricted_insights: str
        is_implicit_purchase_logging_on_android_supported: str
        is_implicit_purchase_logging_on_ios_supported: str
        is_track_android_app_uninstall_supported: str
        is_track_ios_app_uninstall_supported: str
        journey_backfill_status: str
        journey_conversion_events: str
        journey_enabled: str
        journey_timeout: str
        latest_sdk_versions: str
        log_android_implicit_purchase_events: str
        log_automatic_analytics_events: str
        log_implicit_purchase_events: str
        prev_journey_conversion_events: str
        query_approximation_accuracy_level: str
        query_currency: str
        query_timezone: str
        recent_events_update_time: str
        session_timeout_interval: str
        track_android_app_uninstall: str
        track_ios_app_uninstall: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
