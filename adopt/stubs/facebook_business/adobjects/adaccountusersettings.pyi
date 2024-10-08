from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdAccountUserSettings(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        acf_should_opt_out_video_adjustments: str
        aco_sticky_settings: str
        ad_account: str
        ad_object_export_format: str
        auto_review_video_caption: str
        campaign_overview_columns: str
        column_suggestion_status: str
        default_account_overview_agegender_metrics: str
        default_account_overview_location_metrics: str
        default_account_overview_metrics: str
        default_account_overview_time_metrics: str
        default_builtin_column_preset: str
        default_nam_time_range: str
        draft_mode_enabled: str
        export_deleted_items_with_delivery: str
        export_summary_row: str
        has_seen_groups_column_flexing_experience: str
        has_seen_leads_column_flexing_experience: str
        has_seen_shops_ads_metrics_onboarding_tour: str
        has_seen_shops_column_flexing_experience: str
        hidden_optimization_tips: str
        id: str
        is_3p_auth_setting_set: str
        is_text_variation_nux_close: str
        last_used_columns: str
        last_used_pe_filters: str
        last_used_website_urls: str
        outlier_preferences: str
        pinned_ad_object_ids: str
        rb_export_format: str
        rb_export_raw_data: str
        rb_export_summary_row: str
        saip_advertiser_setup_optimisation_guidance_overall_state: str
        saip_advertiser_setup_optimisation_guidance_state: str
        shops_ads_metrics_onboarding_tour_close_count: str
        shops_ads_metrics_onboarding_tour_last_action_time: str
        should_default_image_auto_crop: str
        should_default_image_auto_crop_for_tail: str
        should_default_image_auto_crop_optimization: str
        should_default_image_dof_toggle: str
        should_default_image_lpp_ads_to_square: str
        should_default_instagram_profile_card_optimization: str
        should_default_text_swapping_optimization: str
        should_logout_of_3p_sourcing: str
        show_archived_data: str
        show_text_variation_nux_tooltip: str
        syd_campaign_trends_activemetric: str
        syd_campaign_trends_attribution: str
        syd_campaign_trends_metrics: str
        syd_campaign_trends_objective: str
        syd_campaign_trends_time_range: str
        syd_landing_page_opt_in_status: str
        text_variations_opt_in_type: str
        user: str
    class SydCampaignTrendsObjective:
        app_installs: str
        brand_awareness: str
        event_responses: str
        lead_generation: str
        link_clicks: str
        local_awareness: str
        messages: str
        offer_claims: str
        outcome_app_promotion: str
        outcome_awareness: str
        outcome_engagement: str
        outcome_leads: str
        outcome_sales: str
        outcome_traffic: str
        page_likes: str
        post_engagement: str
        product_catalog_sales: str
        reach: str
        store_visits: str
        video_views: str
        website_conversions: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
