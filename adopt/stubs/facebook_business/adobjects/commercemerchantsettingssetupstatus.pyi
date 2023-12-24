from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CommerceMerchantSettingsSetupStatus(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        deals_setup: str
        marketplace_approval_status: str
        marketplace_approval_status_details: str
        payment_setup: str
        review_status: str
        shop_setup: str
