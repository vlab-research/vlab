from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdAccountCreationRequest(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_accounts_currency: str
        ad_accounts_info: str
        additional_comment: str
        address_in_chinese: str
        address_in_english: str
        address_in_local_language: str
        advertiser_business: str
        appeal_reason: str
        business: str
        business_registration_id: str
        chinese_legal_entity_name: str
        contact: str
        creator: str
        credit_card_id: str
        disapproval_reasons: str
        english_legal_entity_name: str
        extended_credit_id: str
        id: str
        is_smb: str
        is_test: str
        legal_entity_name_in_local_language: str
        oe_request_id: str
        official_website_url: str
        planning_agency_business: str
        planning_agency_business_id: str
        promotable_app_ids: str
        promotable_page_ids: str
        promotable_urls: str
        request_change_reasons: str
        status: str
        subvertical: str
        subvertical_v2: str
        time_created: str
        vertical: str
        vertical_v2: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ad_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
