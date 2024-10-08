from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class BusinessMediaAdPlacementValidationResult(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_placement: str
        ad_placement_label: str
        error_messages: str
        is_valid: str
