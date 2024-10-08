from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.mixins import CanValidate as CanValidate, HasAdLabels as HasAdLabels
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdSet(AbstractCrudObject, HasAdLabels, CanValidate):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        adlabels: str
        adset_schedule: str
        asset_feed_id: str
        attribution_spec: str
        bid_adjustments: str
        bid_amount: str
        bid_constraints: str
        bid_info: str
        bid_strategy: str
        billing_event: str
        budget_remaining: str
        campaign: str
        campaign_active_time: str
        campaign_attribution: str
        campaign_id: str
        configured_status: str
        created_time: str
        creative_sequence: str
        daily_budget: str
        daily_min_spend_target: str
        daily_spend_cap: str
        destination_type: str
        dsa_beneficiary: str
        dsa_payor: str
        effective_status: str
        end_time: str
        existing_customer_budget_percentage: str
        frequency_control_specs: str
        full_funnel_exploration_mode: str
        id: str
        instagram_actor_id: str
        is_budget_schedule_enabled: str
        is_dynamic_creative: str
        issues_info: str
        learning_stage_info: str
        lifetime_budget: str
        lifetime_imps: str
        lifetime_min_spend_target: str
        lifetime_spend_cap: str
        multi_optimization_goal_weight: str
        name: str
        optimization_goal: str
        optimization_sub_event: str
        pacing_type: str
        promoted_object: str
        recommendations: str
        recurring_budget_semantics: str
        regional_regulated_categories: str
        regional_regulation_identities: str
        review_feedback: str
        rf_prediction_id: str
        source_adset: str
        source_adset_id: str
        start_time: str
        status: str
        targeting: str
        targeting_optimization_types: str
        time_based_ad_rotation_id_blocks: str
        time_based_ad_rotation_intervals: str
        updated_time: str
        use_new_app_click: str
        campaign_spec: str
        daily_imps: str
        date_format: str
        execution_options: str
        line_number: str
        rb_prediction_id: str
        time_start: str
        time_stop: str
        topline_id: str
        tune_for_category: str
    class BidStrategy:
        cost_cap: str
        lowest_cost_without_cap: str
        lowest_cost_with_bid_cap: str
        lowest_cost_with_min_roas: str
    class BillingEvent:
        app_installs: str
        clicks: str
        impressions: str
        link_clicks: str
        listing_interaction: str
        none: str
        offer_claims: str
        page_likes: str
        post_engagement: str
        purchase: str
        thruplay: str
    class ConfiguredStatus:
        active: str
        archived: str
        deleted: str
        paused: str
    class EffectiveStatus:
        active: str
        archived: str
        campaign_paused: str
        deleted: str
        in_process: str
        paused: str
        with_issues: str
    class OptimizationGoal:
        ad_recall_lift: str
        app_installs: str
        app_installs_and_offsite_conversions: str
        conversations: str
        derived_events: str
        engaged_users: str
        event_responses: str
        impressions: str
        in_app_value: str
        landing_page_views: str
        lead_generation: str
        link_clicks: str
        meaningful_call_attempt: str
        messaging_appointment_conversion: str
        messaging_purchase_conversion: str
        none: str
        offsite_conversions: str
        page_likes: str
        post_engagement: str
        profile_visit: str
        quality_call: str
        quality_lead: str
        reach: str
        reminders_set: str
        subscribers: str
        thruplay: str
        value: str
        visit_instagram_profile: str
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
    class DestinationType:
        app: str
        applinks_automatic: str
        facebook: str
        instagram_direct: str
        instagram_profile: str
        messaging_instagram_direct_messenger: str
        messaging_instagram_direct_messenger_whatsapp: str
        messaging_instagram_direct_whatsapp: str
        messaging_messenger_whatsapp: str
        messenger: str
        on_ad: str
        on_event: str
        on_page: str
        on_post: str
        on_video: str
        shop_automatic: str
        website: str
        whatsapp: str
    class ExecutionOptions:
        include_recommendations: str
        validate_only: str
    class FullFunnelExplorationMode:
        extended_exploration: str
        limited_exploration: str
        none_exploration: str
    class MultiOptimizationGoalWeight:
        balanced: str
        prefer_event: str
        prefer_install: str
        undefined: str
    class OptimizationSubEvent:
        none: str
        travel_intent: str
        travel_intent_bucket_01: str
        travel_intent_bucket_02: str
        travel_intent_bucket_03: str
        travel_intent_bucket_04: str
        travel_intent_bucket_05: str
        travel_intent_no_destination_intent: str
        trip_consideration: str
        video_sound_on: str
    class RegionalRegulatedCategories:
        value_0: str
        value_1: str
    class TuneForCategory:
        credit: str
        employment: str
        housing: str
        issues_elections_politics: str
        none: str
        online_gambling_and_gaming: str
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
    def get_activities(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ad_studies(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ad_creatives(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_ad_labels(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_ad_label(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ad_rules_governed(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ads(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_async_ad_requests(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_budget_schedule(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_copies(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_copy(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_delivery_estimate(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_insights(self, fields: Incomplete | None = None, params: Incomplete | None = None, is_async: bool = False, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_insights_async(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_targeting_sentence_lines(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
