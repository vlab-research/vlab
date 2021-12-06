from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class MessengerProfile(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        account_linking_url: str = ...
        get_started: str = ...
        greeting: str = ...
        ice_breakers: str = ...
        payment_settings: str = ...
        persistent_menu: str = ...
        target_audience: str = ...
        whitelisted_domains: str = ...