from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class OfflineConversionDataSetPermissions(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        can_edit: str
        can_edit_or_upload: str
        can_upload: str
        should_block_vanilla_business_employee_access: str
