from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class FBPageAndInstagramAccount(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_permissions: str
        bc_permission_status: str
        bc_permissions: str
        is_managed: str
        matched_by: str
