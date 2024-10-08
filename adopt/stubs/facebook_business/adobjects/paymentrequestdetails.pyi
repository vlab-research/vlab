from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class PaymentRequestDetails(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        amount: str
        creation_time: str
        note: str
        payment_request_id: str
        receiver_id: str
        reference_number: str
        sender_id: str
        status: str
        transaction_time: str
