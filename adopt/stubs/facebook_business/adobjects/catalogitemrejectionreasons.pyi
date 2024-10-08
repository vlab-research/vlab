from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CatalogItemRejectionReasons(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        capability: str
        rejection_information: str
    class Capability:
        business_inbox_in_messenger: str
        shops: str
        test_capability: str
        universal_checkout: str
        us_marketplace: str
