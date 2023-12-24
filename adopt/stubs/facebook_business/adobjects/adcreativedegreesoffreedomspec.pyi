from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeDegreesOfFreedomSpec(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_handle_type: str
        creative_features_spec: str
        degrees_of_freedom_type: str
        image_transformation_types: str
        multi_media_transformation_type: str
        stories_transformation_types: str
        text_transformation_types: str
        video_transformation_types: str
