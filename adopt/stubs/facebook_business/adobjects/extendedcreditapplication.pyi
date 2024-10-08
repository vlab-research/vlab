from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class ExtendedCreditApplication(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        billing_country: str
        city: str
        cnpj: str
        country: str
        display_currency: str
        duns_number: str
        id: str
        invoice_email_address: str
        is_umi: str
        legal_entity_name: str
        original_online_limit: str
        phone_number: str
        postal_code: str
        product_types: str
        proposed_credit_limit: str
        registration_number: str
        run_id: str
        state: str
        status: str
        street1: str
        street2: str
        submitter: str
        tax_exempt_status: str
        tax_id: str
        terms: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
