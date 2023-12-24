from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class MessengerProfile(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_linking_url: str
        commands: str
        get_started: str
        greeting: str
        ice_breakers: str
        payment_settings: str
        persistent_menu: str
        subject_to_new_eu_privacy_rules: str
        target_audience: str
        whitelisted_domains: str
