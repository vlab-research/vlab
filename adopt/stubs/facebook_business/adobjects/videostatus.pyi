from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class VideoStatus(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        copyright_check_status: str
        processing_phase: str
        processing_progress: str
        publishing_phase: str
        uploading_phase: str
        video_status: str
