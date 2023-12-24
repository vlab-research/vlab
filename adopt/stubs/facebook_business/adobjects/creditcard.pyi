from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class CreditCard(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        billing_address: str
        card_cobadging: str
        card_holder_name: str
        card_type: str
        credential_id: str
        default_receiving_method_products: str
        expiry_month: str
        expiry_year: str
        id: str
        is_cvv_tricky_bin: str
        is_enabled: str
        is_last_used: str
        is_network_tokenized_in_india: str
        is_soft_disabled: str
        is_user_verified: str
        is_zip_verified: str
        last4: str
        readable_card_type: str
        time_created: str
        time_created_ts: str
        type: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
