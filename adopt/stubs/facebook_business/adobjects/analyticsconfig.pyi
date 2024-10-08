from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AnalyticsConfig(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        analytics_access_for_authorized_ad_account: str
        breakdowns_config: str
        builtin_fields_config: str
        deprecated_events_config: str
        events_config: str
        ios_purchase_validation_secret: str
        is_any_role_able_to_see_restricted_insights: str
        is_implicit_purchase_logging_on_android_supported: str
        is_implicit_purchase_logging_on_ios_supported: str
        is_track_ios_app_uninstall_supported: str
        journey_backfill_status: str
        journey_conversion_events: str
        journey_enabled: str
        journey_impacting_change_time: str
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
        track_ios_app_uninstall: str
