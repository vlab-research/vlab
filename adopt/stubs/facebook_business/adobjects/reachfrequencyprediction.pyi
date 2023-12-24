from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.helpers.reachfrequencypredictionmixin import ReachFrequencyPredictionMixin as ReachFrequencyPredictionMixin
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class ReachFrequencyPrediction(ReachFrequencyPredictionMixin, AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        activity_status: str
        ad_formats: str
        auction_entry_option_index: str
        audience_size_lower_bound: str
        audience_size_upper_bound: str
        business_id: str
        buying_type: str
        campaign_group_id: str
        campaign_id: str
        campaign_time_start: str
        campaign_time_stop: str
        currency: str
        curve_budget_reach: str
        curve_reach: str
        daily_grp_curve: str
        daily_impression_curve: str
        daily_impression_curve_map: str
        day_parting_schedule: str
        destination_id: str
        end_time: str
        expiration_time: str
        external_budget: str
        external_impression: str
        external_maximum_budget: str
        external_maximum_impression: str
        external_maximum_reach: str
        external_minimum_budget: str
        external_minimum_impression: str
        external_minimum_reach: str
        external_reach: str
        feed_ratio_0000: str
        frequency_cap: str
        frequency_distribution_map: str
        frequency_distribution_map_agg: str
        grp_audience_size: str
        grp_avg_probability_map: str
        grp_country_audience_size: str
        grp_curve: str
        grp_dmas_audience_size: str
        grp_filtering_threshold_00: str
        grp_points: str
        grp_ratio: str
        grp_reach_ratio: str
        grp_status: str
        holdout_percentage: str
        id: str
        impression_curve: str
        instagram_destination_id: str
        instream_packages: str
        interval_frequency_cap: str
        interval_frequency_cap_reset_period: str
        is_bonus_media: str
        is_conversion_goal: str
        is_higher_average_frequency: str
        is_io: str
        is_reserved_buying: str
        is_trp: str
        name: str
        objective: str
        objective_name: str
        odax_objective: str
        odax_objective_name: str
        optimization_goal: str
        optimization_goal_name: str
        pause_periods: str
        placement_breakdown: str
        placement_breakdown_map: str
        plan_name: str
        plan_type: str
        prediction_mode: str
        prediction_progress: str
        reference_id: str
        reservation_status: str
        start_time: str
        status: str
        story_event_type: str
        target_cpm: str
        target_spec: str
        time_created: str
        time_updated: str
        timezone_id: str
        timezone_name: str
        topline_id: str
        video_view_length_constraint: str
        viewtag: str
        action: str
        budget: str
        deal_id: str
        destination_ids: str
        exceptions: str
        existing_campaign_id: str
        grp_buying: str
        impression: str
        is_balanced_frequency: str
        is_full_view: str
        is_reach_and_frequency_io_buying: str
        num_curve_points: str
        reach: str
        rf_prediction_id: str
        rf_prediction_id_to_release: str
        rf_prediction_id_to_share: str
        stop_time: str
        target_frequency: str
        target_frequency_reset_period: str
    class Action:
        cancel: str
        quote: str
        reserve: str
    class BuyingType:
        auction: str
        deprecated_reach_block: str
        fixed_cpm: str
        mixed: str
        reachblock: str
        research_poll: str
        reserved: str
    class InstreamPackages:
        beauty: str
        entertainment: str
        food: str
        normal: str
        premium: str
        regular_animals_pets: str
        regular_food: str
        regular_games: str
        regular_politics: str
        regular_sports: str
        regular_style: str
        regular_tv_movies: str
        spanish: str
        sports: str
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
