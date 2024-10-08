from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AudienceSharingAccountValid(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        account_type: str
        business_id: str
        business_name: str
        can_ad_account_use_lookalike_container: str
        sharing_agreement_status: str
