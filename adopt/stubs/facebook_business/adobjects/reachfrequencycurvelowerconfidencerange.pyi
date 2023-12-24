from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ReachFrequencyCurveLowerConfidenceRange(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        impression_lower: str
        num_points: str
        reach: str
        reach_lower: str
        uniq_video_views_2s_lower: str
        video_views_2s_lower: str
