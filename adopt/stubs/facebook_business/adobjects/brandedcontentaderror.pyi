from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class BrandedContentAdError(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        blame_field_spec: str
        error_code: str
        error_description: str
        error_message: str
        error_placement: str
        error_severity: str
        help_center_id: str
