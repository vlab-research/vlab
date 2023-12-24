from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class OmegaCustomerTrx(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_account_ids: str
        advertiser_name: str
        amount: str
        amount_due: str
        billed_amount_details: str
        billing_period: str
        cdn_download_uri: str
        currency: str
        download_uri: str
        due_date: str
        entity: str
        id: str
        invoice_date: str
        invoice_id: str
        invoice_type: str
        liability_type: str
        payment_status: str
        payment_term: str
        type: str
    class Type:
        cm: str
        dm: str
        inv: str
        pro_forma: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_campaigns(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
