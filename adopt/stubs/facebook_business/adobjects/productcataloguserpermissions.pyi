from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ProductCatalogUserPermissions(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        business: str
        business_persona: str
        created_by: str
        created_time: str
        email: str
        role: str
        status: str
        updated_by: str
        updated_time: str
        user: str
