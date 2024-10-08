from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AudioAsset(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        all_ddex_featured_artists: str
        all_ddex_main_artists: str
        audio_cluster_id: str
        cover_image_source: str
        display_artist: str
        download_hd_url: str
        download_sd_url: str
        duration_in_ms: str
        freeform_genre: str
        grid: str
        id: str
        is_test: str
        original_release_date: str
        owner: str
        parental_warning_type: str
        subtitle: str
        title: str
        title_with_featured_artists: str
        upc: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
