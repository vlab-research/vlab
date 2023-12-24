from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ReachFrequencyEstimatesCurve(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        budget: str
        conversion: str
        impression: str
        interpolated_reach: str
        num_points: str
        raw_impression: str
        raw_reach: str
        reach: str
