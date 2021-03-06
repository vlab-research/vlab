from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class ReachFrequencyEstimatesPlacementBreakdown(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        android: str = ...
        audience_network: str = ...
        desktop: str = ...
        ig_android: str = ...
        ig_ios: str = ...
        ig_other: str = ...
        ig_story: str = ...
        instant_articles: str = ...
        instream_videos: str = ...
        ios: str = ...
        msite: str = ...
        suggested_videos: str = ...
