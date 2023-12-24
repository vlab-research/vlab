from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ChatPlugin(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        alignment: str
        desktop_bottom_spacing: str
        desktop_side_spacing: str
        entry_point_icon: str
        entry_point_label: str
        greeting_dialog_display: str
        guest_chat_mode: str
        mobile_bottom_spacing: str
        mobile_chat_display: str
        mobile_side_spacing: str
        theme_color: str
        welcome_screen_greeting: str
