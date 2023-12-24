from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class LiveVideoRecommendedEncoderSettings(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        audio_codec_settings: str
        streaming_protocol: str
        video_codec_settings: str
