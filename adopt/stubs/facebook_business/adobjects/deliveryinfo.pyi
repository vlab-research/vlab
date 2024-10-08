from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class DeliveryInfo(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        active_accelerated_campaign_count: str
        active_day_parted_campaign_count: str
        ad_penalty_map: str
        are_all_daily_budgets_spent: str
        credit_needed_ads_count: str
        eligible_for_delivery_insights: str
        end_time: str
        has_account_hit_spend_limit: str
        has_campaign_group_hit_spend_limit: str
        has_no_active_ads: str
        has_no_ads: str
        inactive_ads_count: str
        inactive_campaign_count: str
        is_account_closed: str
        is_account_disabled: str
        is_ad_uneconomical: str
        is_adfarm_penalized: str
        is_adgroup_partially_rejected: str
        is_campaign_accelerated: str
        is_campaign_completed: str
        is_campaign_day_parted: str
        is_campaign_disabled: str
        is_campaign_group_disabled: str
        is_clickbait_penalized: str
        is_daily_budget_spent: str
        is_engagement_bait_penalized: str
        is_lqwe_penalized: str
        is_reach_and_frequency_misconfigured: str
        is_sensationalism_penalized: str
        is_split_test_active: str
        is_split_test_valid: str
        lift_study_time_period: str
        needs_credit: str
        needs_tax_number: str
        non_deleted_ads_count: str
        not_delivering_campaign_count: str
        pending_ads_count: str
        reach_frequency_campaign_underdelivery_reason: str
        rejected_ads_count: str
        start_time: str
        status: str
        text_penalty_level: str
