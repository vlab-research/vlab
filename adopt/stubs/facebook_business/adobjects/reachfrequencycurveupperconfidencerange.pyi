from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ReachFrequencyCurveUpperConfidenceRange(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        impression_upper: str
        num_points: str
        reach: str
        reach_upper: str
        uniq_video_views_2s_upper: str
        video_views_2s_upper: str
