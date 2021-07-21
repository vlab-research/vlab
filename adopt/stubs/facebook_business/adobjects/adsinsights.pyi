from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.helpers.adsinsightsmixin import AdsInsightsMixin as AdsInsightsMixin
from typing import Any, Optional

class AdsInsights(AdsInsightsMixin, AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        account_currency: str = ...
        account_id: str = ...
        account_name: str = ...
        action_values: str = ...
        actions: str = ...
        ad_bid_type: str = ...
        ad_bid_value: str = ...
        ad_click_actions: str = ...
        ad_delivery: str = ...
        ad_id: str = ...
        ad_impression_actions: str = ...
        ad_name: str = ...
        adset_bid_type: str = ...
        adset_bid_value: str = ...
        adset_budget_type: str = ...
        adset_budget_value: str = ...
        adset_delivery: str = ...
        adset_end: str = ...
        adset_id: str = ...
        adset_name: str = ...
        adset_start: str = ...
        age_targeting: str = ...
        auction_bid: str = ...
        auction_competitiveness: str = ...
        auction_max_competitor_bid: str = ...
        buying_type: str = ...
        campaign_id: str = ...
        campaign_name: str = ...
        canvas_avg_view_percent: str = ...
        canvas_avg_view_time: str = ...
        catalog_segment_value: str = ...
        catalog_segment_value_mobile_purchase_roas: str = ...
        catalog_segment_value_omni_purchase_roas: str = ...
        catalog_segment_value_website_purchase_roas: str = ...
        clicks: str = ...
        conversion_rate_ranking: str = ...
        conversion_values: str = ...
        conversions: str = ...
        cost_per_15_sec_video_view: str = ...
        cost_per_2_sec_continuous_video_view: str = ...
        cost_per_action_type: str = ...
        cost_per_ad_click: str = ...
        cost_per_conversion: str = ...
        cost_per_dda_countby_convs: str = ...
        cost_per_estimated_ad_recallers: str = ...
        cost_per_inline_link_click: str = ...
        cost_per_inline_post_engagement: str = ...
        cost_per_one_thousand_ad_impression: str = ...
        cost_per_outbound_click: str = ...
        cost_per_store_visit_action: str = ...
        cost_per_thruplay: str = ...
        cost_per_unique_action_type: str = ...
        cost_per_unique_click: str = ...
        cost_per_unique_conversion: str = ...
        cost_per_unique_inline_link_click: str = ...
        cost_per_unique_outbound_click: str = ...
        cpc: str = ...
        cpm: str = ...
        cpp: str = ...
        created_time: str = ...
        ctr: str = ...
        date_start: str = ...
        date_stop: str = ...
        dda_countby_convs: str = ...
        engagement_rate_ranking: str = ...
        estimated_ad_recall_rate: str = ...
        estimated_ad_recall_rate_lower_bound: str = ...
        estimated_ad_recall_rate_upper_bound: str = ...
        estimated_ad_recallers: str = ...
        estimated_ad_recallers_lower_bound: str = ...
        estimated_ad_recallers_upper_bound: str = ...
        frequency: str = ...
        full_view_impressions: str = ...
        full_view_reach: str = ...
        gender_targeting: str = ...
        impressions: str = ...
        inline_link_click_ctr: str = ...
        inline_link_clicks: str = ...
        inline_post_engagement: str = ...
        instant_experience_clicks_to_open: str = ...
        instant_experience_clicks_to_start: str = ...
        instant_experience_outbound_clicks: str = ...
        labels: str = ...
        location: str = ...
        mobile_app_purchase_roas: str = ...
        objective: str = ...
        outbound_clicks: str = ...
        outbound_clicks_ctr: str = ...
        place_page_name: str = ...
        purchase_roas: str = ...
        qualifying_question_qualify_answer_rate: str = ...
        quality_ranking: str = ...
        quality_score_ectr: str = ...
        quality_score_ecvr: str = ...
        quality_score_organic: str = ...
        reach: str = ...
        social_spend: str = ...
        spend: str = ...
        store_visit_actions: str = ...
        unique_actions: str = ...
        unique_clicks: str = ...
        unique_conversions: str = ...
        unique_ctr: str = ...
        unique_inline_link_click_ctr: str = ...
        unique_inline_link_clicks: str = ...
        unique_link_clicks_ctr: str = ...
        unique_outbound_clicks: str = ...
        unique_outbound_clicks_ctr: str = ...
        unique_video_continuous_2_sec_watched_actions: str = ...
        unique_video_view_15_sec: str = ...
        updated_time: str = ...
        video_15_sec_watched_actions: str = ...
        video_30_sec_watched_actions: str = ...
        video_avg_time_watched_actions: str = ...
        video_continuous_2_sec_watched_actions: str = ...
        video_p100_watched_actions: str = ...
        video_p25_watched_actions: str = ...
        video_p50_watched_actions: str = ...
        video_p75_watched_actions: str = ...
        video_p95_watched_actions: str = ...
        video_play_actions: str = ...
        video_play_curve_actions: str = ...
        video_play_retention_0_to_15s_actions: str = ...
        video_play_retention_20_to_60s_actions: str = ...
        video_play_retention_graph_actions: str = ...
        video_thruplay_watched_actions: str = ...
        video_time_watched_actions: str = ...
        website_ctr: str = ...
        website_purchase_roas: str = ...
        wish_bid: str = ...
    class ActionAttributionWindows:
        value_1d_click: str = ...
        value_1d_view: str = ...
        value_28d_click: str = ...
        value_28d_view: str = ...
        value_7d_click: str = ...
        value_7d_view: str = ...
        dda: str = ...
        value_default: str = ...
    class ActionBreakdowns:
        action_canvas_component_name: str = ...
        action_carousel_card_id: str = ...
        action_carousel_card_name: str = ...
        action_destination: str = ...
        action_device: str = ...
        action_reaction: str = ...
        action_target_id: str = ...
        action_type: str = ...
        action_video_sound: str = ...
        action_video_type: str = ...
    class ActionReportTime:
        conversion: str = ...
        impression: str = ...
    class Breakdowns:
        ad_format_asset: str = ...
        age: str = ...
        body_asset: str = ...
        call_to_action_asset: str = ...
        country: str = ...
        description_asset: str = ...
        device_platform: str = ...
        dma: str = ...
        frequency_value: str = ...
        gender: str = ...
        hourly_stats_aggregated_by_advertiser_time_zone: str = ...
        hourly_stats_aggregated_by_audience_time_zone: str = ...
        image_asset: str = ...
        impression_device: str = ...
        link_url_asset: str = ...
        place_page_id: str = ...
        platform_position: str = ...
        product_id: str = ...
        publisher_platform: str = ...
        region: str = ...
        title_asset: str = ...
        video_asset: str = ...
    class DatePreset:
        last_14d: str = ...
        last_28d: str = ...
        last_30d: str = ...
        last_3d: str = ...
        last_7d: str = ...
        last_90d: str = ...
        last_month: str = ...
        last_quarter: str = ...
        last_week_mon_sun: str = ...
        last_week_sun_sat: str = ...
        last_year: str = ...
        lifetime: str = ...
        this_month: str = ...
        this_quarter: str = ...
        this_week_mon_today: str = ...
        this_week_sun_today: str = ...
        this_year: str = ...
        today: str = ...
        yesterday: str = ...
    class Level:
        account: str = ...
        ad: str = ...
        adset: str = ...
        campaign: str = ...
    class SummaryActionBreakdowns:
        action_canvas_component_name: str = ...
        action_carousel_card_id: str = ...
        action_carousel_card_name: str = ...
        action_destination: str = ...
        action_device: str = ...
        action_reaction: str = ...
        action_target_id: str = ...
        action_type: str = ...
        action_video_sound: str = ...
        action_video_type: str = ...
    @classmethod
    def get_endpoint(cls): ...