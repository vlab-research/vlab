from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativePhotoData(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        branded_content_shared_to_sponsor_status: str
        branded_content_sponsor_page_id: str
        caption: str
        image_hash: str
        page_welcome_message: str
        url: str
