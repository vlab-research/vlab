from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class PageAboutStoryComposedBlock(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        depth: str
        entity_ranges: str
        inline_style_ranges: str
        text: str
        type: str
