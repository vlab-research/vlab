from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeVideoDataCustomOverlaySpec(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        background_color: str
        background_opacity: str
        duration: str
        float_with_margin: str
        full_width: str
        option: str
        position: str
        start: str
        template: str
        text_color: str
    class BackgroundOpacity:
        half: str
        solid: str
    class Option:
        bank_transfer: str
        boleto: str
        cash_on_delivery: str
        discount_with_boleto: str
        fast_delivery: str
        free_shipping: str
        home_delivery: str
        inventory: str
        pay_at_hotel: str
        pay_on_arrival: str
    class Position:
        middle_center: str
        middle_left: str
        middle_right: str
        top_center: str
        top_left: str
        top_right: str
    class Template:
        rectangle_with_text: str
