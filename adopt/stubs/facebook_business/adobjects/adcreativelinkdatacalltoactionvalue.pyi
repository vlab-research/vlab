from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeLinkDataCallToActionValue(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        app_destination: str
        app_link: str
        application: str
        event_id: str
        lead_gen_form_id: str
        link: str
        link_caption: str
        link_format: str
        page: str
        product_link: str
        whatsapp_number: str
