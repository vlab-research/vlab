from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class PaymentSubscription(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        amount: str
        app_param_data: str
        application: str
        billing_period: str
        canceled_reason: str
        created_time: str
        currency: str
        id: str
        last_payment: str
        next_bill_time: str
        next_period_amount: str
        next_period_currency: str
        next_period_product: str
        payment_status: str
        pending_cancel: str
        period_start_time: str
        product: str
        status: str
        test: str
        trial_amount: str
        trial_currency: str
        trial_expiry_time: str
        updated_time: str
        user: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
