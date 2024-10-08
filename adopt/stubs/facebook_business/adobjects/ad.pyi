from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.mixins import HasAdLabels as HasAdLabels
from facebook_business.typechecker import TypeChecker as TypeChecker

class Ad(AbstractCrudObject, HasAdLabels):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        ad_active_time: str
        ad_review_feedback: str
        ad_schedule_end_time: str
        ad_schedule_start_time: str
        adlabels: str
        adset: str
        adset_id: str
        bid_amount: str
        bid_info: str
        bid_type: str
        campaign: str
        campaign_id: str
        configured_status: str
        conversion_domain: str
        conversion_specs: str
        created_time: str
        creative: str
        creative_asset_groups_spec: str
        demolink_hash: str
        display_sequence: str
        effective_status: str
        engagement_audience: str
        failed_delivery_checks: str
        id: str
        issues_info: str
        last_updated_by_app_id: str
        name: str
        preview_shareable_link: str
        priority: str
        recommendations: str
        source_ad: str
        source_ad_id: str
        status: str
        targeting: str
        tracking_and_conversion_with_defaults: str
        tracking_specs: str
        updated_time: str
        adset_spec: str
        audience_id: str
        date_format: str
        draft_adgroup_id: str
        execution_options: str
        include_demolink_hashes: str
        filename: str
    class BidType:
        absolute_ocpm: str
        cpa: str
        cpc: str
        cpm: str
        multi_premium: str
    class ConfiguredStatus:
        active: str
        archived: str
        deleted: str
        paused: str
    class EffectiveStatus:
        active: str
        adset_paused: str
        archived: str
        campaign_paused: str
        deleted: str
        disapproved: str
        in_process: str
        paused: str
        pending_billing_info: str
        pending_review: str
        preapproved: str
        with_issues: str
    class Status:
        active: str
        archived: str
        deleted: str
        paused: str
    class DatePreset:
        data_maximum: str
        last_14d: str
        last_28d: str
        last_30d: str
        last_3d: str
        last_7d: str
        last_90d: str
        last_month: str
        last_quarter: str
        last_week_mon_sun: str
        last_week_sun_sat: str
        last_year: str
        maximum: str
        this_month: str
        this_quarter: str
        this_week_mon_today: str
        this_week_sun_today: str
        this_year: str
        today: str
        yesterday: str
    class ExecutionOptions:
        include_recommendations: str
        synchronous_ad_review: str
        validate_only: str
    class Operator:
        all: str
        any: str
    class StatusOption:
        active: str
        inherited_from_source: str
        paused: str
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ad_creatives(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_ad_label(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ad_rules_governed(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_copies(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_copy(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_insights(self, fields: Incomplete | None = None, params: Incomplete | None = None, is_async: bool = False, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_insights_async(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_leads(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_previews(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_targeting_sentence_lines(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
