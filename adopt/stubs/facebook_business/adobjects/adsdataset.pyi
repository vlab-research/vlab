from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdsDataset(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        can_proxy: str
        collection_rate: str
        config: str
        creation_time: str
        creator: str
        dataset_id: str
        description: str
        duplicate_entries: str
        enable_auto_assign_to_accounts: str
        enable_automatic_events: str
        enable_automatic_matching: str
        enable_real_time_event_log: str
        event_stats: str
        event_time_max: str
        event_time_min: str
        first_party_cookie_status: str
        has_bapi_domains: str
        has_catalog_microdata_activity: str
        has_ofa_redacted_keys: str
        has_sent_pii: str
        id: str
        is_consolidated_container: str
        is_created_by_business: str
        is_crm: str
        is_eligible_for_sharing_to_ad_account: str
        is_eligible_for_sharing_to_business: str
        is_eligible_for_value_optimization: str
        is_mta_use: str
        is_restricted_use: str
        is_unavailable: str
        last_fired_time: str
        last_upload_app: str
        last_upload_app_changed_time: str
        last_upload_time: str
        late_upload_reminder_eligibility: str
        match_rate_approx: str
        matched_entries: str
        name: str
        no_ads_tracked_for_weekly_uploaded_events_reminder_eligibility: str
        num_active_ad_set_tracked: str
        num_recent_offline_conversions_uploaded: str
        num_uploads: str
        owner_ad_account: str
        owner_business: str
        percentage_of_late_uploads_in_external_suboptimal_window: str
        permissions: str
        server_last_fired_time: str
        show_automatic_events: str
        upload_rate: str
        upload_reminder_eligibility: str
        usage: str
        valid_entries: str
