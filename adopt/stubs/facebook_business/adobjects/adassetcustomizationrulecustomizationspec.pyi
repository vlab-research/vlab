from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAssetCustomizationRuleCustomizationSpec(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        age_max: str
        age_min: str
        audience_network_positions: str
        device_platforms: str
        facebook_positions: str
        geo_locations: str
        instagram_positions: str
        locales: str
        messenger_positions: str
        publisher_platforms: str
    class DevicePlatforms:
        desktop: str
        mobile: str
