from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdsUserSettings(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        a_plus_c_survey_seen: str
        adgroup_name_template: str
        ads_tool_visits: str
        aplusc_carousel_cda_opt_in_status: str
        aplusc_carousel_inline_comment_opt_in_status: str
        aplusc_epa_opt_in_status: str
        aplusc_opt_out_friction: str
        autoflow_lite_opt_in_status: str
        autoflow_lite_should_opt_in: str
        blended_ads_creation_defaulting_opt_in_status: str
        bookmarked_pages: str
        campaign_group_name_template: str
        campaign_name_template: str
        carousel_to_video_opt_in_status: str
        connected_sources_catalog_opt_in_status: str
        default_creation_mode: str
        export_format_default: str
        focus_mode_default: str
        gen_ai_alpha_test_status: str
        id: str
        image_expansion_opt_in_status: str
        is_ads_ai_consented: str
        is_cbo_default_on: str
        is_se_removal_guidance_dismissed: str
        last_used_post_format: str
        last_visited_time: str
        multi_ads_settings: str
        music_on_reels_opt_in: str
        muted_cbo_midflight_education_messages: str
        onsite_destination_optimization_opt_in: str
        open_tabs: str
        previously_seen_recommendations: str
        product_extensions_opt_in: str
        selected_ad_account: str
        selected_comparison_timerange: str
        selected_metric_cic: str
        selected_metrics_cic: str
        selected_page: str
        selected_page_section: str
        selected_power_editor_pane: str
        selected_stat_range: str
        should_export_filter_empty_cols: str
        should_export_rows_without_unsupported_feature: str
        should_not_auto_expand_tree_table: str
        should_not_show_cbo_campaign_toggle_off_confirmation_message: str
        should_not_show_publish_message_on_editor_close: str
        show_original_videos_opt_in: str
        static_ad_product_extensions_opt_in: str
        sticky_setting_after_default_on: str
        syd_campaign_trends_metric: str
        total_coupon_syd_dismissals: str
        total_coupon_upsell_dismissals: str
        use_pe_create_flow: str
        use_stepper_primary_entry: str
        user: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
