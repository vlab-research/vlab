from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdsTextSuggestions(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_account_id: str
        bodies: str
        descriptions: str
        inactive_session_tally: str
        long: str
        short: str
        titles: str
