from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CTWAWhatsAppNumbersInfo(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        can_manage_wa_flows: str
        formatted_whatsapp_number: str
        is_business_number: str
        page_whatsapp_number_id: str
        whatsapp_number: str
        whatsapp_smb_device: str
