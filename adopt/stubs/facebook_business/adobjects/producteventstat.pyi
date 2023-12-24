from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ProductEventStat(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        date_start: str
        date_stop: str
        device_type: str
        event: str
        event_source: str
        total_content_ids_matched_other_catalogs: str
        total_matched_content_ids: str
        total_unmatched_content_ids: str
        unique_content_ids_matched_other_catalogs: str
        unique_matched_content_ids: str
        unique_unmatched_content_ids: str
    class DeviceType:
        desktop: str
        mobile_android_phone: str
        mobile_android_tablet: str
        mobile_ipad: str
        mobile_iphone: str
        mobile_ipod: str
        mobile_phone: str
        mobile_tablet: str
        mobile_windows_phone: str
        unknown: str
    class Event:
        addtocart: str
        addtowishlist: str
        initiatecheckout: str
        lead: str
        purchase: str
        search: str
        subscribe: str
        viewcontent: str
    class Breakdowns:
        device_type: str
