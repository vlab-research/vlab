from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class McomInvoiceBankAccount(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        num_pending_verification_accounts: str
        num_verified_accounts: str
        pending_verification_accounts: str
        verified_accounts: str
