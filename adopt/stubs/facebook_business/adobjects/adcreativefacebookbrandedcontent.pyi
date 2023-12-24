from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeFacebookBrandedContent(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        shared_to_sponsor_status: str
        sponsor_page_id: str
        sponsor_relationship: str
