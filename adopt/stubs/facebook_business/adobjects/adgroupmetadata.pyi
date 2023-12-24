from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdgroupMetadata(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_standard_enhancements_edit_source: str
        adgroup_creation_source: str
        adgroup_edit_source: str
        carousel_style: str
        carousel_with_static_card_style: str
