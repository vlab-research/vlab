from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdvertiserVerificationStatus(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        banner_type: str
        grace_period_ends_at: str
        ufac_redirect_uri: str
        verification_status: str
