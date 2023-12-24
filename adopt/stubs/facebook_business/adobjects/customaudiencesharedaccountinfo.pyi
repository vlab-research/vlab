from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CustomAudiencesharedAccountInfo(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        account_name: str
        business_id: str
        business_name: str
        sharing_status: str
