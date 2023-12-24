from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ReachFrequencyEstimatesPlacementBreakdown(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        android: str
        audience_network: str
        desktop: str
        facebook_search: str
        fb_reels: str
        fb_reels_overlay: str
        ig_android: str
        ig_ios: str
        ig_other: str
        ig_reels: str
        ig_story: str
        instant_articles: str
        instream_videos: str
        ios: str
        msite: str
        suggested_videos: str
