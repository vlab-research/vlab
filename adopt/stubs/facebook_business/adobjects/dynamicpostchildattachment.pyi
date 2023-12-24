from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class DynamicPostChildAttachment(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        description: str
        image_url: str
        link: str
        place_id: str
        product_id: str
        title: str
