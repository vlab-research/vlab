from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class McomInvoiceDetails(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        additional_amounts: str
        buyer_notes: str
        currency_amount: str
        external_invoice_id: str
        features: str
        invoice_created: str
        invoice_id: str
        invoice_instructions: str
        invoice_instructions_image_url: str
        invoice_updated: str
        outstanding_amount: str
        paid_amount: str
        payments: str
        platform_logo_url: str
        platform_name: str
        product_items: str
        shipping_address: str
        status: str
        tracking_info: str
