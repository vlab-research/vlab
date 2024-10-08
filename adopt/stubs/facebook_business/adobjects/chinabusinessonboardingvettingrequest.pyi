from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class ChinaBusinessOnboardingVettingRequest(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_account_creation_request_status: str
        ad_account_limit: str
        ad_account_number: str
        ad_accounts_info: str
        business_manager_id: str
        business_registration: str
        business_registration_id: str
        chinese_address: str
        chinese_legal_entity_name: str
        city: str
        contact: str
        coupon_code: str
        disapprove_reason: str
        english_business_name: str
        id: str
        official_website_url: str
        org_ad_account_count: str
        payment_type: str
        planning_agency_id: str
        planning_agency_name: str
        promotable_app_ids: str
        promotable_page_ids: str
        promotable_pages: str
        promotable_urls: str
        request_changes_reason: str
        reviewed_user: str
        spend_limit: str
        status: str
        subvertical: str
        subvertical_v2: str
        supporting_document: str
        time_changes_requested: str
        time_created: str
        time_updated: str
        time_zone: str
        used_reseller_link: str
        user_id: str
        user_name: str
        vertical: str
        vertical_v2: str
        viewed_by_reseller: str
        zip_code: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
