from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class VideoCopyright(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        content_category: str
        copyright_content_id: str
        creator: str
        excluded_ownership_segments: str
        id: str
        in_conflict: str
        monitoring_status: str
        monitoring_type: str
        ownership_countries: str
        reference_file: str
        reference_file_disabled: str
        reference_file_disabled_by_ops: str
        reference_owner_id: str
        rule_ids: str
        tags: str
        whitelisted_ids: str
    class ContentCategory:
        episode: str
        movie: str
        web: str
    class MonitoringType:
        audio_only: str
        video_and_audio: str
        video_only: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_update_records(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
