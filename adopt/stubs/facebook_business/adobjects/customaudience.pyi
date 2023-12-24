from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.helpers.customaudiencemixin import CustomAudienceMixin as CustomAudienceMixin
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class CustomAudience(CustomAudienceMixin, AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        approximate_count_lower_bound: str
        approximate_count_upper_bound: str
        customer_file_source: str
        data_source: str
        data_source_types: str
        datafile_custom_audience_uploading_status: str
        delete_time: str
        delivery_status: str
        description: str
        excluded_custom_audiences: str
        external_event_source: str
        household_audience: str
        id: str
        included_custom_audiences: str
        is_household: str
        is_snapshot: str
        is_value_based: str
        lookalike_audience_ids: str
        lookalike_spec: str
        name: str
        operation_status: str
        opt_out_link: str
        owner_business: str
        page_deletion_marked_delete_time: str
        permission_for_actions: str
        pixel_id: str
        regulated_audience_spec: str
        retention_days: str
        rev_share_policy_id: str
        rule: str
        rule_aggregation: str
        rule_v2: str
        seed_audience: str
        sharing_status: str
        subtype: str
        time_content_updated: str
        time_created: str
        time_updated: str
        allowed_domains: str
        associated_audience_id: str
        claim_objective: str
        content_type: str
        countries: str
        creation_params: str
        dataset_id: str
        enable_fetch_or_create: str
        event_source_group: str
        event_sources: str
        exclusions: str
        inclusions: str
        list_of_accounts: str
        origin_audience_id: str
        parent_audience_id: str
        partner_reference_key: str
        prefill: str
        product_set_id: str
        use_in_campaigns: str
        video_group_ids: str
        whats_app_business_phone_number_id: str
    class ClaimObjective:
        automotive_model: str
        collaborative_ads: str
        home_listing: str
        media_title: str
        product: str
        travel: str
        vehicle: str
        vehicle_offer: str
    class ContentType:
        automotive_model: str
        destination: str
        flight: str
        home_listing: str
        hotel: str
        job: str
        local_service_business: str
        location_based_item: str
        media_title: str
        offline_product: str
        product: str
        vehicle: str
        vehicle_offer: str
    class CustomerFileSource:
        both_user_and_partner_provided: str
        partner_provided_only: str
        user_provided_only: str
    class Subtype:
        app: str
        bag_of_accounts: str
        bidding: str
        claim: str
        custom: str
        engagement: str
        fox: str
        lookalike: str
        managed: str
        measurement: str
        offline_conversion: str
        partner: str
        primary: str
        regulated_categories_audience: str
        study_rule_audience: str
        subscriber_segment: str
        video: str
        website: str
    class ActionSource:
        physical_store: str
        website: str
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_ad_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ad_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_ad_account(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ads(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_sessions(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_shared_account_info(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_users(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_user(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_users_replace(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
