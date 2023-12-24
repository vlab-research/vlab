from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class PagePostExperiment(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        auto_resolve_settings: str
        control_video_id: str
        creation_time: str
        creator: str
        declared_winning_time: str
        declared_winning_video_id: str
        description: str
        experiment_video_ids: str
        id: str
        insight_snapshots: str
        name: str
        optimization_goal: str
        publish_status: str
        publish_time: str
        scheduled_experiment_timestamp: str
        updated_time: str
    class OptimizationGoal:
        auto_resolve_to_control: str
        avg_time_watched: str
        comments: str
        impressions: str
        impressions_unique: str
        link_clicks: str
        other: str
        reactions: str
        reels_plays: str
        shares: str
        video_views_60s: str
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_video_insights(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
