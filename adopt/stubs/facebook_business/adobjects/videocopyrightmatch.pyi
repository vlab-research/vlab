from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class VideoCopyrightMatch(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        created_date: str
        id: str
        last_modified_user: str
        match_data: str
        match_status: str
        notes: str
        permalink: str
    class Action:
        block: str
        claim_ad_earnings: str
        manual_review: str
        monitor: str
        request_takedown: str
    class ActionReason:
        article_17_preflagging: str
        artist_objection: str
        objectionable_content: str
        premium_music_video: str
        prerelease_content: str
        product_parameters: str
        restricted_content: str
        unauthorized_commercial_use: str
    class MatchContentType:
        audio_only: str
        video_and_audio: str
        video_only: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
