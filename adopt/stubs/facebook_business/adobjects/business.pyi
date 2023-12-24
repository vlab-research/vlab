from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.helpers.businessmixin import BusinessMixin as BusinessMixin
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class Business(BusinessMixin, AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        block_offline_analytics: str
        collaborative_ads_managed_partner_business_info: str
        collaborative_ads_managed_partner_eligibility: str
        collaborative_ads_partner_premium_options: str
        created_by: str
        created_time: str
        extended_updated_time: str
        id: str
        is_hidden: str
        link: str
        name: str
        payment_account_id: str
        primary_page: str
        profile_picture_uri: str
        timezone_id: str
        two_factor_type: str
        updated_by: str
        updated_time: str
        user_access_expire_time: str
        verification_status: str
        vertical: str
        vertical_id: str
    class TwoFactorType:
        admin_required: str
        all_required: str
        none: str
    class Vertical:
        advertising: str
        automotive: str
        consumer_packaged_goods: str
        ecommerce: str
        education: str
        energy_and_utilities: str
        entertainment_and_media: str
        financial_services: str
        gaming: str
        government_and_politics: str
        health: str
        luxury: str
        marketing: str
        non_profit: str
        organizations_and_associations: str
        other: str
        professional_services: str
        restaurant: str
        retail: str
        technology: str
        telecom: str
        travel: str
    class PermittedTasks:
        advertise: str
        analyze: str
        cashier_role: str
        create_content: str
        manage: str
        manage_jobs: str
        manage_leads: str
        messaging: str
        moderate: str
        moderate_community: str
        pages_messaging: str
        pages_messaging_subscriptions: str
        profile_plus_advertise: str
        profile_plus_analyze: str
        profile_plus_create_content: str
        profile_plus_facebook_access: str
        profile_plus_full_control: str
        profile_plus_manage: str
        profile_plus_manage_leads: str
        profile_plus_messaging: str
        profile_plus_moderate: str
        profile_plus_moderate_delegate_community: str
        profile_plus_revenue: str
        read_page_mailboxes: str
        view_monetization_insights: str
    class SurveyBusinessType:
        advertiser: str
        agency: str
        app_developer: str
        publisher: str
    class PagePermittedTasks:
        advertise: str
        analyze: str
        cashier_role: str
        create_content: str
        manage: str
        manage_jobs: str
        manage_leads: str
        messaging: str
        moderate: str
        moderate_community: str
        pages_messaging: str
        pages_messaging_subscriptions: str
        profile_plus_advertise: str
        profile_plus_analyze: str
        profile_plus_create_content: str
        profile_plus_facebook_access: str
        profile_plus_full_control: str
        profile_plus_manage: str
        profile_plus_manage_leads: str
        profile_plus_messaging: str
        profile_plus_moderate: str
        profile_plus_moderate_delegate_community: str
        profile_plus_revenue: str
        read_page_mailboxes: str
        view_monetization_insights: str
    class SubverticalV2:
        accounting_and_tax: str
        activities_and_leisure: str
        air: str
        apparel_and_accessories: str
        arts_and_heritage_and_education: str
        ar_or_vr_gaming: str
        audio_streaming: str
        auto: str
        auto_insurance: str
        auto_rental: str
        baby: str
        ballot_initiative_or_referendum: str
        beauty: str
        beauty_and_fashion: str
        beer_and_wine_and_liquor_and_malt_beverages: str
        bookstores: str
        broadcast_television: str
        business_consultants: str
        buying_agency: str
        cable_and_satellite: str
        cable_television: str
        call_center_and_messaging_services: str
        candidate_or_politician: str
        career: str
        career_and_tech: str
        casual_dining: str
        chronic_conditions_and_medical_causes: str
        civic_influencers: str
        clinical_trials: str
        coffee: str
        computer_and_software_and_hardware: str
        console_and_cross_platform_gaming: str
        consulting: str
        consumer_electronics: str
        counseling_and_psychotherapy: str
        creative_agency: str
        credit_and_financing_and_mortages: str
        cruises_and_marine: str
        culture_and_lifestyle: str
        data_analytics_and_data_management: str
        dating_and_technology_apps: str
        department_store: str
        desktop_software: str
        dieting_and_fitness_programs: str
        digital_native_education_or_training: str
        drinking_places: str
        education_resources: str
        ed_tech: str
        elearning_and_massive_online_open_courses: str
        election_commission: str
        electronics_and_appliances: str
        engineering_and_design: str
        environment_and_animal_welfare: str
        esports: str
        events: str
        farming_and_ranching: str
        file_storage_and_cloud_and_data_services: str
        finance: str
        fin_tech: str
        fishing_and_hunting_and_forestry_and_logging: str
        fitness: str
        food: str
        footwear: str
        for_profit_colleges_and_universities: str
        full_service_agency: str
        government_controlled_entity: str
        government_department_or_agency: str
        government_official: str
        government_owned_media: str
        grocery_and_drug_and_convenience: str
        head_of_state: str
        health_insurance: str
        health_systems_and_practitioners: str
        health_tech: str
        home_and_furniture_and_office: str
        home_improvement: str
        home_insurance: str
        home_tech: str
        hotel_and_accomodation: str
        household_goods_durable: str
        household_goods_non_durable: str
        hr_and_financial_management: str
        humanitarian_or_disaster_relief: str
        independent_expenditure_group: str
        insurance_tech: str
        international_organizaton: str
        investment_bank_and_brokerage: str
        issue_advocacy: str
        legal: str
        life_insurance: str
        logistics_and_transportation_and_fleet_management: str
        manufacturing: str
        medical_devices_and_supplies_and_equipment: str
        medspa_and_elective_surgeries_and_alternative_medicine: str
        mining_and_quarrying: str
        mobile_gaming: str
        movies: str
        museums_and_parks_and_libraries: str
        music: str
        network_security_products: str
        news_and_current_events: str
        non_prescription: str
        not_for_profit_colleges_and_universities: str
        office: str
        office_or_business_supplies: str
        oil_and_gas_and_consumable_fuel: str
        online_only_publications: str
        package_or_freight_delivery: str
        party_independent_expenditure_group_us: str
        payment_processing_and_gateway_solutions: str
        pc_gaming: str
        people: str
        personal_care: str
        pet: str
        photography_and_filming_services: str
        pizza: str
        planning_agency: str
        political_party_or_committee: str
        prescription: str
        professional_associations: str
        property_and_casualty: str
        quick_service: str
        radio: str
        railroads: str
        real_estate: str
        real_money_gaming: str
        recreational: str
        religious: str
        reseller: str
        residential_and_long_term_care_facilities_and_outpatient_care_centers: str
        retail_and_credit_union_and_commercial_bank: str
        ride_sharing_or_taxi_services: str
        safety_services: str
        scholarly: str
        school_and_early_children_edcation: str
        social_media: str
        software_as_a_service: str
        sporting: str
        sporting_and_outdoor: str
        sports: str
        superstores: str
        t1_automotive_manufacturer: str
        t1_motorcycle: str
        t2_dealer_associations: str
        t3_auto_agency: str
        t3_auto_resellers: str
        t3_dealer_groups: str
        t3_franchise_dealer: str
        t3_independent_dealer: str
        t3_parts_and_services: str
        t3_portals: str
        telecommunications_equipment_and_accessories: str
        telephone_service_providers_and_carriers: str
        ticketing: str
        tobacco: str
        tourism_and_travel_services: str
        tourism_board: str
        toy_and_hobby: str
        trade_school: str
        travel_agencies_and_guides_and_otas: str
        utilities_and_energy_equipment_and_services: str
        veterinary_clinics_and_services: str
        video_streaming: str
        virtual_services: str
        vitamins_or_wellness: str
        warehousing_and_storage: str
        water_and_soft_drink_and_baverage: str
        website_designers_or_graphic_designers: str
        wholesale: str
        wireless_services: str
    class VerticalV2:
        advertising_and_marketing: str
        agriculture: str
        automotive: str
        banking_and_credit_cards: str
        business_to_business: str
        consumer_packaged_goods: str
        ecommerce: str
        education: str
        energy_and_natural_resources_and_utilities: str
        entertainment_and_media: str
        gaming: str
        government: str
        healthcare_and_pharmaceuticals_and_biotech: str
        insurance: str
        non_profit: str
        organizations_and_associations: str
        politics: str
        professional_services: str
        publishing: str
        restaurants: str
        retail: str
        technology: str
        telecom: str
        travel: str
    class ActionSource:
        physical_store: str
        website: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_access_token(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_ad_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ad_studies(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_ad_study(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_ad_account(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_add_phone_number(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_ad_network_application(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ad_network_analytics(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_ad_network_analytic(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ad_network_analytics_results(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ads_reporting_mmm_reports(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ads_reporting_mmm_schedulers(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ads_pixels(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_ads_pixel(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_agencies(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_agencies(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_an_placements(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_block_list_draft(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_business_asset_groups(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_business_invoices(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_business_users(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_business_user(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_business_projects(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_claim_custom_conversion(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_client_ad_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_client_apps(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_client_app(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_client_offsite_signal_container_business_objects(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_client_pages(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_client_page(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_client_pixels(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_client_product_catalogs(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_client_whats_app_business_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_clients(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_clients(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_collaborative_ads_collaboration_requests(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_collaborative_ads_collaboration_request(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_collaborative_ads_suggested_partners(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_commerce_merchant_settings(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_cpas_business_setup_config(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_cpas_business_setup_config(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_cpas_merchant_config(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_creative_folder(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_credit_cards(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_custom_conversion(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_draft_negative_keyword_list(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_event_source_groups(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_event_source_group(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_extended_credit_applications(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_extended_credits(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_image(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_initiated_audience_sharing_requests(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_instagram_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_instagram_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_instagram_business_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_managed_businesses(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_managed_business(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_managed_partner_business_setup(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_managed_partner_businesses(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_managed_partner_business(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_negative_keyword_lists(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_offline_conversion_data_sets(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_offline_conversion_data_set(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_open_bridge_configurations(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_open_bridge_configuration(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_owned_ad_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_owned_ad_account(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_owned_apps(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_owned_app(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_owned_businesses(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_owned_businesses(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_owned_business(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_owned_instagram_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_owned_offsite_signal_container_business_objects(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_owned_pages(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_owned_page(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_owned_pixels(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_owned_product_catalogs(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_owned_product_catalog(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_owned_whats_app_business_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_pages(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_partner_account_linking(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_partner_premium_option(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_pending_client_ad_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_pending_client_apps(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_pending_client_pages(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_pending_owned_ad_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_pending_owned_pages(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_pending_shared_offsite_signal_container_business_objects(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_pending_users(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_picture(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_pixel_to(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_pre_verified_numbers(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_received_audience_sharing_requests(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_setup_managed_partner_ad_account(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_share_pre_verified_numbers(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_share_pre_verified_number(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_system_user_access_token(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_system_users(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_system_user(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_third_party_measurement_report_dataset(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_video(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
