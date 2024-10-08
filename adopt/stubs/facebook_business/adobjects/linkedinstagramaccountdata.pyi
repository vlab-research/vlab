from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class LinkedInstagramAccountData(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        access_token: str
        analytics_claim: str
        full_name: str
        profile_picture_url: str
        user_id: str
        user_name: str
