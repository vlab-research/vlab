from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class McomInvoiceStatus(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        bank_account_number: str
        bank_code: str
        invoice_id: str
        invoice_status: str
        page_id: str
        payment_method: str
        payment_type: str
        payout_amount: str
        slip_verification_error: str
        slip_verification_status: str
        transaction_fee: str
        transfer_slip: str
