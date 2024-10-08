from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class InstagramInsightsResult(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        description: str
        id: str
        name: str
        period: str
        title: str
        total_value: str
        values: str
    class Breakdown:
        action_type: str
        follow_type: str
        story_navigation_action_type: str
        surface_type: str
    class Metric:
        clips_replays_count: str
        comments: str
        follows: str
        ig_reels_aggregated_all_plays_count: str
        ig_reels_avg_watch_time: str
        ig_reels_video_view_total_time: str
        impressions: str
        likes: str
        navigation: str
        plays: str
        profile_activity: str
        profile_visits: str
        reach: str
        replies: str
        saved: str
        shares: str
        total_interactions: str
        video_views: str
    class Period:
        day: str
        days_28: str
        lifetime: str
        month: str
        total_over_range: str
        week: str
    class MetricType:
        value_default: str
        time_series: str
        total_value: str
    class Timeframe:
        last_14_days: str
        last_30_days: str
        last_90_days: str
        prev_month: str
        this_month: str
        this_week: str
