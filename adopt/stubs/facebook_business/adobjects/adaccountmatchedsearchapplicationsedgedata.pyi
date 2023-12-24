from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAccountMatchedSearchApplicationsEdgeData(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        app_id: str
        are_app_events_unavailable: str
        icon_url: str
        name: str
        search_source_store: str
        store: str
        unique_id: str
        url: str
    class AppStore:
        amazon_app_store: str
        apk_mirror: str
        apk_monk: str
        apk_pure: str
        aptoide_a1_store: str
        bemobi_mobile_store: str
        digital_turbine_store: str
        does_not_exist: str
        fb_android_store: str
        fb_canvas: str
        fb_gameroom: str
        galaxy_store: str
        google_play: str
        instant_game: str
        itunes: str
        itunes_ipad: str
        neon_android_store: str
        none: str
        oculus_app_store: str
        oppo: str
        roku_store: str
        uptodown: str
        vivo: str
        windows_10_store: str
        windows_store: str
        xiaomi: str
