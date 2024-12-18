from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeLinkDataCustomOverlaySpec(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        background_color: str
        float_with_margin: str
        font: str
        option: str
        position: str
        render_with_icon: str
        template: str
        text_color: str
    class BackgroundColor:
        background_000000: str
        background_0090ff: str
        background_00af4c: str
        background_595959: str
        background_755dde: str
        background_e50900: str
        background_f23474: str
        background_f78400: str
        background_ffffff: str
    class Font:
        droid_serif_regular: str
        lato_regular: str
        noto_sans_regular: str
        nunito_sans_bold: str
        open_sans_bold: str
        pt_serif_bold: str
        roboto_condensed_regular: str
        roboto_medium: str
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
        bottom_left: str
        bottom_right: str
        top_left: str
        top_right: str
    class Template:
        pill_with_text: str
    class TextColor:
        text_000000: str
        text_007ad0: str
        text_009c2a: str
        text_646464: str
        text_755dde: str
        text_c91b00: str
        text_f23474: str
        text_f78400: str
        text_ffffff: str
