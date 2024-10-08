from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class Transaction(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        app_amount: str
        billing_end_time: str
        billing_reason: str
        billing_start_time: str
        card_charge_mode: str
        charge_type: str
        checkout_campaign_group_id: str
        credential_id: str
        fatura_id: str
        id: str
        is_business_ec_charge: str
        is_funding_event: str
        payment_option: str
        product_type: str
        provider_amount: str
        status: str
        time: str
        tracking_id: str
        transaction_type: str
        tx_type: str
        vat_invoice_id: str
    class ProductType:
        cp_return_label: str
        facebook_ad: str
        ig_ad: str
        whatsapp: str
        workplace: str
    @classmethod
    def get_endpoint(cls): ...
