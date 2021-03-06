from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.helpers.customaudiencemixin import CustomAudienceMixin as CustomAudienceMixin
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker
from typing import Any, Optional

class CustomAudience(CustomAudienceMixin, AbstractCrudObject):
    def __init__(self, fbid: Optional[Any] = ..., parent_id: Optional[Any] = ..., api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str = ...
        approximate_count: str = ...
        customer_file_source: str = ...
        data_source: str = ...
        data_source_types: str = ...
        datafile_custom_audience_uploading_status: str = ...
        delivery_status: str = ...
        description: str = ...
        excluded_custom_audiences: str = ...
        external_event_source: str = ...
        household_audience: str = ...
        id: str = ...
        included_custom_audiences: str = ...
        is_household: str = ...
        is_snapshot: str = ...
        is_value_based: str = ...
        lookalike_audience_ids: str = ...
        lookalike_spec: str = ...
        name: str = ...
        operation_status: str = ...
        opt_out_link: str = ...
        permission_for_actions: str = ...
        pixel_id: str = ...
        regulated_audience_spec: str = ...
        retention_days: str = ...
        rev_share_policy_id: str = ...
        rule: str = ...
        rule_aggregation: str = ...
        rule_v2: str = ...
        seed_audience: str = ...
        sharing_status: str = ...
        subtype: str = ...
        time_content_updated: str = ...
        time_created: str = ...
        time_updated: str = ...
        accountid: str = ...
        additionalmetadata: str = ...
        allowed_domains: str = ...
        associated_audience_id: str = ...
        claim_objective: str = ...
        content_type: str = ...
        countries: str = ...
        creation_params: str = ...
        dataset_id: str = ...
        details: str = ...
        enable_fetch_or_create: str = ...
        event_source_group: str = ...
        event_sources: str = ...
        exclusions: str = ...
        expectedsize: str = ...
        gender: str = ...
        inclusions: str = ...
        isprivate: str = ...
        is_household_exclusion: str = ...
        list_of_accounts: str = ...
        maxage: str = ...
        minage: str = ...
        origin_audience_id: str = ...
        parent_audience_id: str = ...
        partnerid: str = ...
        partner_reference_key: str = ...
        prefill: str = ...
        product_set_id: str = ...
        source: str = ...
        tags: str = ...
        video_group_ids: str = ...
    class ClaimObjective:
        automotive_model: str = ...
        collaborative_ads: str = ...
        home_listing: str = ...
        media_title: str = ...
        product: str = ...
        travel: str = ...
        vehicle: str = ...
        vehicle_offer: str = ...
    class ContentType:
        automotive_model: str = ...
        destination: str = ...
        flight: str = ...
        home_listing: str = ...
        hotel: str = ...
        local_service_business: str = ...
        location_based_item: str = ...
        media_title: str = ...
        offline_product: str = ...
        product: str = ...
        vehicle: str = ...
        vehicle_offer: str = ...
    class CustomerFileSource:
        both_user_and_partner_provided: str = ...
        partner_provided_only: str = ...
        user_provided_only: str = ...
    class Subtype:
        app: str = ...
        bag_of_accounts: str = ...
        claim: str = ...
        custom: str = ...
        engagement: str = ...
        fox: str = ...
        lookalike: str = ...
        managed: str = ...
        measurement: str = ...
        offline_conversion: str = ...
        partner: str = ...
        regulated_categories_audience: str = ...
        study_rule_audience: str = ...
        video: str = ...
        website: str = ...
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id: Any, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def api_delete(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def api_get(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def api_update(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def delete_ad_accounts(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_ad_accounts(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def create_ad_account(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_ads(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_sessions(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_shared_account_info(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def delete_users(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def create_user(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
