from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class PhotoMetadata(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        camera_make: str
        camera_model: str
        datetime_modified: str
        datetime_taken: str
        exposure: str
        focal_length: str
        fstop: str
        iso_speed: str
        offline_id: str
        orientation: str
        original_height: str
        original_width: str
