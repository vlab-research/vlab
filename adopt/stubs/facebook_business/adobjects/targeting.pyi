from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class Targeting(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        adgroup_id: str
        age_max: str
        age_min: str
        age_range: str
        alternate_auto_targeting_option: str
        app_install_state: str
        audience_network_positions: str
        behaviors: str
        brand_safety_content_filter_levels: str
        catalog_based_targeting: str
        cities: str
        college_years: str
        connections: str
        contextual_targeting_categories: str
        countries: str
        country: str
        country_groups: str
        custom_audiences: str
        device_platforms: str
        direct_install_devices: str
        dynamic_audience_ids: str
        education_majors: str
        education_schools: str
        education_statuses: str
        effective_audience_network_positions: str
        effective_device_platforms: str
        effective_facebook_positions: str
        effective_instagram_positions: str
        effective_messenger_positions: str
        effective_publisher_platforms: str
        engagement_specs: str
        ethnic_affinity: str
        exclude_reached_since: str
        excluded_brand_safety_content_types: str
        excluded_connections: str
        excluded_custom_audiences: str
        excluded_dynamic_audience_ids: str
        excluded_engagement_specs: str
        excluded_geo_locations: str
        excluded_mobile_device_model: str
        excluded_product_audience_specs: str
        excluded_publisher_categories: str
        excluded_publisher_list_ids: str
        excluded_user_device: str
        exclusions: str
        facebook_positions: str
        family_statuses: str
        fb_deal_id: str
        flexible_spec: str
        friends_of_connections: str
        genders: str
        generation: str
        geo_locations: str
        home_ownership: str
        home_type: str
        home_value: str
        household_composition: str
        income: str
        industries: str
        instagram_positions: str
        instream_video_skippable_excluded: str
        interested_in: str
        interests: str
        is_whatsapp_destination_ad: str
        keywords: str
        life_events: str
        locales: str
        messenger_positions: str
        moms: str
        net_worth: str
        office_type: str
        place_page_set_ids: str
        political_views: str
        politics: str
        product_audience_specs: str
        prospecting_audience: str
        publisher_platforms: str
        radius: str
        regions: str
        relationship_statuses: str
        site_category: str
        targeting_automation: str
        targeting_optimization: str
        targeting_relaxation_types: str
        user_adclusters: str
        user_device: str
        user_event: str
        user_os: str
        wireless_carrier: str
        work_employers: str
        work_positions: str
        zips: str
    class DevicePlatforms:
        desktop: str
        mobile: str
    class EffectiveDevicePlatforms:
        desktop: str
        mobile: str
