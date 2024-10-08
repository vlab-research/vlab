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
        not_set: str
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
    class TimezoneId:
        value_0: str
        value_1: str
        value_2: str
        value_3: str
        value_4: str
        value_5: str
        value_6: str
        value_7: str
        value_8: str
        value_9: str
        value_10: str
        value_11: str
        value_12: str
        value_13: str
        value_14: str
        value_15: str
        value_16: str
        value_17: str
        value_18: str
        value_19: str
        value_20: str
        value_21: str
        value_22: str
        value_23: str
        value_24: str
        value_25: str
        value_26: str
        value_27: str
        value_28: str
        value_29: str
        value_30: str
        value_31: str
        value_32: str
        value_33: str
        value_34: str
        value_35: str
        value_36: str
        value_37: str
        value_38: str
        value_39: str
        value_40: str
        value_41: str
        value_42: str
        value_43: str
        value_44: str
        value_45: str
        value_46: str
        value_47: str
        value_48: str
        value_49: str
        value_50: str
        value_51: str
        value_52: str
        value_53: str
        value_54: str
        value_55: str
        value_56: str
        value_57: str
        value_58: str
        value_59: str
        value_60: str
        value_61: str
        value_62: str
        value_63: str
        value_64: str
        value_65: str
        value_66: str
        value_67: str
        value_68: str
        value_69: str
        value_70: str
        value_71: str
        value_72: str
        value_73: str
        value_74: str
        value_75: str
        value_76: str
        value_77: str
        value_78: str
        value_79: str
        value_80: str
        value_81: str
        value_82: str
        value_83: str
        value_84: str
        value_85: str
        value_86: str
        value_87: str
        value_88: str
        value_89: str
        value_90: str
        value_91: str
        value_92: str
        value_93: str
        value_94: str
        value_95: str
        value_96: str
        value_97: str
        value_98: str
        value_99: str
        value_100: str
        value_101: str
        value_102: str
        value_103: str
        value_104: str
        value_105: str
        value_106: str
        value_107: str
        value_108: str
        value_109: str
        value_110: str
        value_111: str
        value_112: str
        value_113: str
        value_114: str
        value_115: str
        value_116: str
        value_117: str
        value_118: str
        value_119: str
        value_120: str
        value_121: str
        value_122: str
        value_123: str
        value_124: str
        value_125: str
        value_126: str
        value_127: str
        value_128: str
        value_129: str
        value_130: str
        value_131: str
        value_132: str
        value_133: str
        value_134: str
        value_135: str
        value_136: str
        value_137: str
        value_138: str
        value_139: str
        value_140: str
        value_141: str
        value_142: str
        value_143: str
        value_144: str
        value_145: str
        value_146: str
        value_147: str
        value_148: str
        value_149: str
        value_150: str
        value_151: str
        value_152: str
        value_153: str
        value_154: str
        value_155: str
        value_156: str
        value_157: str
        value_158: str
        value_159: str
        value_160: str
        value_161: str
        value_162: str
        value_163: str
        value_164: str
        value_165: str
        value_166: str
        value_167: str
        value_168: str
        value_169: str
        value_170: str
        value_171: str
        value_172: str
        value_173: str
        value_174: str
        value_175: str
        value_176: str
        value_177: str
        value_178: str
        value_179: str
        value_180: str
        value_181: str
        value_182: str
        value_183: str
        value_184: str
        value_185: str
        value_186: str
        value_187: str
        value_188: str
        value_189: str
        value_190: str
        value_191: str
        value_192: str
        value_193: str
        value_194: str
        value_195: str
        value_196: str
        value_197: str
        value_198: str
        value_199: str
        value_200: str
        value_201: str
        value_202: str
        value_203: str
        value_204: str
        value_205: str
        value_206: str
        value_207: str
        value_208: str
        value_209: str
        value_210: str
        value_211: str
        value_212: str
        value_213: str
        value_214: str
        value_215: str
        value_216: str
        value_217: str
        value_218: str
        value_219: str
        value_220: str
        value_221: str
        value_222: str
        value_223: str
        value_224: str
        value_225: str
        value_226: str
        value_227: str
        value_228: str
        value_229: str
        value_230: str
        value_231: str
        value_232: str
        value_233: str
        value_234: str
        value_235: str
        value_236: str
        value_237: str
        value_238: str
        value_239: str
        value_240: str
        value_241: str
        value_242: str
        value_243: str
        value_244: str
        value_245: str
        value_246: str
        value_247: str
        value_248: str
        value_249: str
        value_250: str
        value_251: str
        value_252: str
        value_253: str
        value_254: str
        value_255: str
        value_256: str
        value_257: str
        value_258: str
        value_259: str
        value_260: str
        value_261: str
        value_262: str
        value_263: str
        value_264: str
        value_265: str
        value_266: str
        value_267: str
        value_268: str
        value_269: str
        value_270: str
        value_271: str
        value_272: str
        value_273: str
        value_274: str
        value_275: str
        value_276: str
        value_277: str
        value_278: str
        value_279: str
        value_280: str
        value_281: str
        value_282: str
        value_283: str
        value_284: str
        value_285: str
        value_286: str
        value_287: str
        value_288: str
        value_289: str
        value_290: str
        value_291: str
        value_292: str
        value_293: str
        value_294: str
        value_295: str
        value_296: str
        value_297: str
        value_298: str
        value_299: str
        value_300: str
        value_301: str
        value_302: str
        value_303: str
        value_304: str
        value_305: str
        value_306: str
        value_307: str
        value_308: str
        value_309: str
        value_310: str
        value_311: str
        value_312: str
        value_313: str
        value_314: str
        value_315: str
        value_316: str
        value_317: str
        value_318: str
        value_319: str
        value_320: str
        value_321: str
        value_322: str
        value_323: str
        value_324: str
        value_325: str
        value_326: str
        value_327: str
        value_328: str
        value_329: str
        value_330: str
        value_331: str
        value_332: str
        value_333: str
        value_334: str
        value_335: str
        value_336: str
        value_337: str
        value_338: str
        value_339: str
        value_340: str
        value_341: str
        value_342: str
        value_343: str
        value_344: str
        value_345: str
        value_346: str
        value_347: str
        value_348: str
        value_349: str
        value_350: str
        value_351: str
        value_352: str
        value_353: str
        value_354: str
        value_355: str
        value_356: str
        value_357: str
        value_358: str
        value_359: str
        value_360: str
        value_361: str
        value_362: str
        value_363: str
        value_364: str
        value_365: str
        value_366: str
        value_367: str
        value_368: str
        value_369: str
        value_370: str
        value_371: str
        value_372: str
        value_373: str
        value_374: str
        value_375: str
        value_376: str
        value_377: str
        value_378: str
        value_379: str
        value_380: str
        value_381: str
        value_382: str
        value_383: str
        value_384: str
        value_385: str
        value_386: str
        value_387: str
        value_388: str
        value_389: str
        value_390: str
        value_391: str
        value_392: str
        value_393: str
        value_394: str
        value_395: str
        value_396: str
        value_397: str
        value_398: str
        value_399: str
        value_400: str
        value_401: str
        value_402: str
        value_403: str
        value_404: str
        value_405: str
        value_406: str
        value_407: str
        value_408: str
        value_409: str
        value_410: str
        value_411: str
        value_412: str
        value_413: str
        value_414: str
        value_415: str
        value_416: str
        value_417: str
        value_418: str
        value_419: str
        value_420: str
        value_421: str
        value_422: str
        value_423: str
        value_424: str
        value_425: str
        value_426: str
        value_427: str
        value_428: str
        value_429: str
        value_430: str
        value_431: str
        value_432: str
        value_433: str
        value_434: str
        value_435: str
        value_436: str
        value_437: str
        value_438: str
        value_439: str
        value_440: str
        value_441: str
        value_442: str
        value_443: str
        value_444: str
        value_445: str
        value_446: str
        value_447: str
        value_448: str
        value_449: str
        value_450: str
        value_451: str
        value_452: str
        value_453: str
        value_454: str
        value_455: str
        value_456: str
        value_457: str
        value_458: str
        value_459: str
        value_460: str
        value_461: str
        value_462: str
        value_463: str
        value_464: str
        value_465: str
        value_466: str
        value_467: str
        value_468: str
        value_469: str
        value_470: str
        value_471: str
        value_472: str
        value_473: str
        value_474: str
        value_475: str
        value_476: str
        value_477: str
        value_478: str
        value_479: str
        value_480: str
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
    def delete_m_an_age_d_businesses(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_m_an_age_d_business(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_m_an_age_d_partner_business_setup(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_m_an_age_d_partner_businesses(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_m_an_age_d_partner_business(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_negative_keyword_lists(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
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
    def get_pending_share_d_offsite_signal_container_business_objects(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_pending_users(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_picture(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_pixel_to(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_pre_verified_numbers(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_received_audience_sharing_requests(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_reseller_guidances(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_self_certified_whatsapp_business_submissions(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_setup_m_an_age_d_partner_ad_account(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_share_pre_verified_numbers(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_share_pre_verified_number(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_system_user_access_token(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_system_users(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_system_user(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_third_party_measurement_report_dataset(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_video(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
